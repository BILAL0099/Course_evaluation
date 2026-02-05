"""
SCORM package extraction utilities.
"""

import zipfile
import asyncio
from pathlib import Path
from typing import Optional


class SCORMExtractor:
    """Handles extraction of SCORM ZIP packages."""
    
    def __init__(self):
        self.manifest_names = ["imsmanifest.xml", "IMSMANIFEST.XML"]
    
    async def extract(self, zip_path: Path, extract_path: Path) -> Path:
        """
        Extract a SCORM ZIP package.
        
        Args:
            zip_path: Path to the ZIP file
            extract_path: Directory to extract to
            
        Returns:
            Path to the extracted directory
            
        Raises:
            ValueError: If the ZIP is invalid or not a SCORM package
        """
        # Run extraction in thread pool to not block async
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, 
            self._extract_sync, 
            zip_path, 
            extract_path
        )
    
    def _extract_sync(self, zip_path: Path, extract_path: Path) -> Path:
        """Synchronous extraction implementation."""
        if not zip_path.exists():
            raise FileNotFoundError(f"ZIP file not found: {zip_path}")
        
        # Create extraction directory
        extract_path.mkdir(parents=True, exist_ok=True)
        
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # Validate it's a proper ZIP
                if zip_ref.testzip() is not None:
                    raise ValueError("Corrupted ZIP file")
                
                # Check for manifest
                manifest_found = self._find_manifest_in_zip(zip_ref)
                if not manifest_found:
                    raise ValueError("Not a valid SCORM package: imsmanifest.xml not found")
                
                # Extract all files
                zip_ref.extractall(extract_path)
                
        except zipfile.BadZipFile:
            raise ValueError("Invalid ZIP file format")
        
        # Verify manifest exists after extraction
        manifest_path = self._find_manifest(extract_path)
        if not manifest_path:
            raise ValueError("Manifest not found after extraction")
        
        return extract_path
    
    def _find_manifest_in_zip(self, zip_ref: zipfile.ZipFile) -> Optional[str]:
        """Find the manifest file within the ZIP."""
        names = zip_ref.namelist()
        
        for manifest_name in self.manifest_names:
            # Check root level
            if manifest_name in names:
                return manifest_name
            
            # Check one level deep (common in some SCORM packages)
            for name in names:
                if name.endswith(f"/{manifest_name}") or name.endswith(f"\\{manifest_name}"):
                    parts = name.replace("\\", "/").split("/")
                    if len(parts) == 2:  # Only one directory level
                        return name
        
        return None
    
    def _find_manifest(self, extract_path: Path) -> Optional[Path]:
        """Find the manifest file in the extracted directory."""
        for manifest_name in self.manifest_names:
            # Check root level
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
    
    async def get_file_list(self, zip_path: Path) -> list[str]:
        """
        Get list of files in a SCORM package without extracting.
        
        Args:
            zip_path: Path to the ZIP file
            
        Returns:
            List of file paths in the ZIP
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._get_file_list_sync, zip_path)
    
    def _get_file_list_sync(self, zip_path: Path) -> list[str]:
        """Synchronous file listing implementation."""
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            return zip_ref.namelist()
    
    async def validate(self, zip_path: Path) -> dict:
        """
        Validate a SCORM package without extracting.
        
        Args:
            zip_path: Path to the ZIP file
            
        Returns:
            Validation result with is_valid and details
        """
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, self._validate_sync, zip_path)
            return result
        except Exception as e:
            return {
                "is_valid": False,
                "error": str(e)
            }
    
    def _validate_sync(self, zip_path: Path) -> dict:
        """Synchronous validation implementation."""
        result = {
            "is_valid": False,
            "has_manifest": False,
            "file_count": 0,
            "total_size": 0,
            "scorm_type": None
        }
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            names = zip_ref.namelist()
            result["file_count"] = len(names)
            
            # Calculate total size
            for info in zip_ref.infolist():
                result["total_size"] += info.file_size
            
            # Check for manifest
            manifest_name = self._find_manifest_in_zip(zip_ref)
            if manifest_name:
                result["has_manifest"] = True
                result["is_valid"] = True
                
                # Try to determine SCORM version from manifest
                try:
                    manifest_content = zip_ref.read(manifest_name).decode('utf-8')
                    if "adlcp:scormType" in manifest_content or "adlcp:scormtype" in manifest_content:
                        result["scorm_type"] = "SCORM 1.2"
                    if "adlseq:" in manifest_content or "imsss:" in manifest_content:
                        result["scorm_type"] = "SCORM 2004"
                except:
                    pass
        
        return result
