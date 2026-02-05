"""
SCORM manifest parser.
"""

import asyncio
from pathlib import Path
from typing import Optional, List, Dict
from lxml import etree

from src.schemas import SCORMManifest


class SCORMParser:
    """Parses SCORM imsmanifest.xml files."""
    
    # Common SCORM namespaces
    NAMESPACES = {
        'imscp': 'http://www.imsproject.org/xsd/imscp_rootv1p1p2',
        'adlcp': 'http://www.adlnet.org/xsd/adlcp_rootv1p2',
        'imsmd': 'http://www.imsglobal.org/xsd/imsmd_rootv1p2p1',
        'xsi': 'http://www.w3.org/2001/XMLSchema-instance',
        # SCORM 2004
        'adlseq': 'http://www.adlnet.org/xsd/adlseq_v1p3',
        'imsss': 'http://www.imsglobal.org/xsd/imsss',
    }
    
    def __init__(self):
        self.manifest_names = ["imsmanifest.xml", "IMSMANIFEST.XML"]
    
    async def parse(self, extract_path: Path) -> SCORMManifest:
        """
        Parse the SCORM manifest from an extracted package.
        
        Args:
            extract_path: Path to the extracted SCORM directory
            
        Returns:
            Parsed SCORMManifest object
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._parse_sync, extract_path)
    
    def _parse_sync(self, extract_path: Path) -> SCORMManifest:
        """Synchronous parsing implementation."""
        manifest_path = self._find_manifest(extract_path)
        if not manifest_path:
            raise FileNotFoundError("imsmanifest.xml not found")
        
        # Parse XML
        tree = etree.parse(str(manifest_path))
        root = tree.getroot()
        
        # Detect namespaces
        nsmap = self._build_namespace_map(root)
        
        # Extract manifest info
        identifier = root.get('identifier', 'unknown')
        
        # Get title from organizations or metadata
        title = self._get_title(root, nsmap)
        
        # Get version
        version = self._get_version(root, nsmap)
        
        # Determine SCORM version
        scorm_version = self._detect_scorm_version(root, nsmap)
        
        # Get resources
        resources = self._get_resources(root, nsmap)
        
        # Get organizations
        organizations = self._get_organizations(root, nsmap)
        
        # Find launch file
        launch_file = self._find_launch_file(root, nsmap, resources)
        
        # Make launch file path relative to extract_path
        if launch_file:
            # Handle if manifest is in subdirectory
            manifest_dir = manifest_path.parent
            if manifest_dir != extract_path:
                relative_dir = manifest_dir.relative_to(extract_path)
                launch_file = str(relative_dir / launch_file)
        
        return SCORMManifest(
            identifier=identifier,
            title=title,
            version=version,
            launch_file=launch_file or "index.html",
            resources=resources,
            organizations=organizations,
            scorm_version=scorm_version
        )
    
    def _find_manifest(self, extract_path: Path) -> Optional[Path]:
        """Find the manifest file."""
        for manifest_name in self.manifest_names:
            manifest_path = extract_path / manifest_name
            if manifest_path.exists():
                return manifest_path
            
            # Check immediate subdirectories
            for subdir in extract_path.iterdir():
                if subdir.is_dir():
                    manifest_path = subdir / manifest_name
                    if manifest_path.exists():
                        return manifest_path
        
        return None
    
    def _build_namespace_map(self, root) -> Dict[str, str]:
        """Build namespace map from root element."""
        nsmap = dict(root.nsmap)
        # Remove None key if present
        if None in nsmap:
            nsmap['default'] = nsmap.pop(None)
        # Add standard namespaces
        for prefix, uri in self.NAMESPACES.items():
            if prefix not in nsmap:
                nsmap[prefix] = uri
        return nsmap
    
    def _get_title(self, root, nsmap: Dict[str, str]) -> str:
        """Extract course title from manifest."""
        # Try organizations/organization/title first
        title_paths = [
            './/organizations/organization/title',
            './/imscp:organizations/imscp:organization/imscp:title',
            './/default:organizations/default:organization/default:title',
            './/metadata/lom/general/title/langstring',
            './/imsmd:lom/imsmd:general/imsmd:title/imsmd:langstring',
        ]
        
        for path in title_paths:
            try:
                # Handle namespace in path
                if ':' in path and path.split(':')[0].split('/')[-1] in nsmap:
                    elements = root.xpath(path, namespaces=nsmap)
                else:
                    elements = root.xpath(path)
                
                if elements and elements[0].text:
                    return elements[0].text.strip()
            except:
                continue
        
        # Fallback to manifest identifier
        return root.get('identifier', 'Untitled Course')
    
    def _get_version(self, root, nsmap: Dict[str, str]) -> Optional[str]:
        """Extract version from manifest."""
        version = root.get('version')
        if version:
            return version
        
        # Try metadata
        try:
            version_elem = root.xpath('.//metadata/schemaversion')
            if version_elem:
                return version_elem[0].text
        except:
            pass
        
        return None
    
    def _detect_scorm_version(self, root, nsmap: Dict[str, str]) -> str:
        """Detect SCORM version from manifest content."""
        xml_str = etree.tostring(root, encoding='unicode')
        
        # Check for SCORM 2004 indicators
        if 'adlseq' in xml_str or 'imsss' in xml_str:
            return "2004"
        
        # Check for SCORM 1.2 indicators
        if 'adlcp' in xml_str:
            # Could be either, check schemaversion
            try:
                schema_elem = root.xpath('.//metadata/schemaversion')
                if schema_elem:
                    schema = schema_elem[0].text
                    if '2004' in schema:
                        return "2004"
                    elif '1.2' in schema:
                        return "1.2"
            except:
                pass
            return "1.2"
        
        return "1.2"  # Default to 1.2
    
    def _get_resources(self, root, nsmap: Dict[str, str]) -> List[Dict]:
        """Extract resources from manifest."""
        resources = []
        
        # Try different paths for resources
        resource_paths = [
            './/resources/resource',
            './/imscp:resources/imscp:resource',
            './/default:resources/default:resource',
        ]
        
        for path in resource_paths:
            try:
                if ':' in path and path.split(':')[0].split('/')[-1] in nsmap:
                    elements = root.xpath(path, namespaces=nsmap)
                else:
                    elements = root.xpath(path)
                
                if elements:
                    for elem in elements:
                        resource = {
                            'identifier': elem.get('identifier'),
                            'type': elem.get('type'),
                            'href': elem.get('href'),
                            'scorm_type': elem.get('{http://www.adlnet.org/xsd/adlcp_rootv1p2}scormType') or 
                                         elem.get('scormType') or
                                         elem.get('{http://www.adlnet.org/xsd/adlcp_v1p3}scormType'),
                        }
                        
                        # Get files within resource
                        files = []
                        for file_elem in elem.findall('.//{*}file'):
                            href = file_elem.get('href')
                            if href:
                                files.append(href)
                        resource['files'] = files
                        
                        resources.append(resource)
                    break
            except Exception as e:
                continue
        
        return resources
    
    def _get_organizations(self, root, nsmap: Dict[str, str]) -> List[Dict]:
        """Extract organizations/structure from manifest."""
        organizations = []
        
        org_paths = [
            './/organizations/organization',
            './/imscp:organizations/imscp:organization',
            './/default:organizations/default:organization',
        ]
        
        for path in org_paths:
            try:
                if ':' in path and path.split(':')[0].split('/')[-1] in nsmap:
                    elements = root.xpath(path, namespaces=nsmap)
                else:
                    elements = root.xpath(path)
                
                if elements:
                    for elem in elements:
                        org = {
                            'identifier': elem.get('identifier'),
                            'title': None,
                            'items': []
                        }
                        
                        # Get title
                        title_elem = elem.find('.//{*}title')
                        if title_elem is not None and title_elem.text:
                            org['title'] = title_elem.text.strip()
                        
                        # Get items (structure)
                        org['items'] = self._parse_items(elem)
                        
                        organizations.append(org)
                    break
            except:
                continue
        
        return organizations
    
    def _parse_items(self, parent) -> List[Dict]:
        """Recursively parse item structure."""
        items = []
        
        for item in parent.findall('.//{*}item'):
            # Only direct children
            if item.getparent() != parent:
                continue
                
            item_data = {
                'identifier': item.get('identifier'),
                'identifierref': item.get('identifierref'),
                'title': None,
                'children': []
            }
            
            title_elem = item.find('.//{*}title')
            if title_elem is not None and title_elem.text:
                item_data['title'] = title_elem.text.strip()
            
            # Recursively get children
            item_data['children'] = self._parse_items(item)
            
            items.append(item_data)
        
        return items
    
    def _find_launch_file(self, root, nsmap: Dict[str, str], resources: List[Dict]) -> Optional[str]:
        """Find the launch file (SCO entry point)."""
        # Get default organization
        try:
            orgs_elem = root.find('.//{*}organizations')
            default_org_id = orgs_elem.get('default') if orgs_elem is not None else None
        except:
            default_org_id = None
        
        # Find the first item's identifierref
        item_ref = None
        
        for org in self._get_organizations(root, nsmap):
            if default_org_id and org.get('identifier') != default_org_id:
                continue
            
            # Find first item with identifierref
            def find_first_ref(items):
                for item in items:
                    if item.get('identifierref'):
                        return item.get('identifierref')
                    if item.get('children'):
                        ref = find_first_ref(item['children'])
                        if ref:
                            return ref
                return None
            
            item_ref = find_first_ref(org.get('items', []))
            if item_ref:
                break
        
        # Find resource by identifier
        for resource in resources:
            if resource.get('identifier') == item_ref:
                return resource.get('href')
            
            # Also check if it's a SCO type
            if resource.get('scorm_type') == 'sco' and resource.get('href'):
                return resource.get('href')
        
        # Fallback: return first resource with href
        for resource in resources:
            if resource.get('href'):
                return resource.get('href')
        
        return None
