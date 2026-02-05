/**
 * SCORM API Stub - Fake LMS API for testing SCORM courses
 * 
 * This stub creates both SCORM 1.2 (window.API) and 
 * SCORM 2004 (window.API_1484_11) interfaces.
 * 
 * All SCORM calls are tracked in window.__SCORM__ for inspection.
 */

(function() {
    'use strict';
    
    // Initialize tracking object
    window.__SCORM__ = {
        version: null,
        initialized: false,
        terminated: false,
        calls: [],
        data: {},
        errors: [],
        lastError: '0',
        startTime: Date.now()
    };
    
    // Helper to log calls
    function logCall(api, method, args, result) {
        const call = {
            api: api,
            method: method,
            args: Array.from(args),
            result: result,
            timestamp: Date.now(),
            elapsed: Date.now() - window.__SCORM__.startTime
        };
        window.__SCORM__.calls.push(call);
        console.log(`[SCORM ${api}] ${method}(${JSON.stringify(args)}) => ${result}`);
        return result;
    }
    
    // Default CMI data for SCORM 1.2
    const cmiData12 = {
        'cmi.core.student_id': 'test_student_001',
        'cmi.core.student_name': 'Test, Student',
        'cmi.core.lesson_location': '',
        'cmi.core.lesson_status': 'not attempted',
        'cmi.core.entry': 'ab-initio',
        'cmi.core.score.raw': '',
        'cmi.core.score.min': '0',
        'cmi.core.score.max': '100',
        'cmi.core.total_time': '0000:00:00',
        'cmi.core.exit': '',
        'cmi.core.session_time': '',
        'cmi.core.credit': 'credit',
        'cmi.core.lesson_mode': 'normal',
        'cmi.suspend_data': '',
        'cmi.launch_data': '',
        'cmi.comments': '',
        'cmi.objectives._count': '0',
        'cmi.interactions._count': '0',
        'cmi.student_preference.audio': '0',
        'cmi.student_preference.language': '',
        'cmi.student_preference.speed': '0',
        'cmi.student_preference.text': '0'
    };
    
    // Default CMI data for SCORM 2004
    const cmiData2004 = {
        'cmi.learner_id': 'test_student_001',
        'cmi.learner_name': 'Test, Student',
        'cmi.location': '',
        'cmi.completion_status': 'unknown',
        'cmi.success_status': 'unknown',
        'cmi.entry': 'ab-initio',
        'cmi.score.raw': '',
        'cmi.score.min': '0',
        'cmi.score.max': '100',
        'cmi.score.scaled': '',
        'cmi.total_time': 'PT0H0M0S',
        'cmi.exit': '',
        'cmi.session_time': '',
        'cmi.credit': 'credit',
        'cmi.mode': 'normal',
        'cmi.suspend_data': '',
        'cmi.launch_data': '',
        'cmi.comments_from_learner._count': '0',
        'cmi.comments_from_lms._count': '0',
        'cmi.objectives._count': '0',
        'cmi.interactions._count': '0',
        'cmi.learner_preference.audio_level': '1',
        'cmi.learner_preference.language': '',
        'cmi.learner_preference.delivery_speed': '1',
        'cmi.learner_preference.audio_captioning': '0',
        'cmi.progress_measure': '',
        'cmi.scaled_passing_score': ''
    };
    
    // SCORM 1.2 Error codes
    const errors12 = {
        '0': 'No Error',
        '101': 'General Exception',
        '201': 'Invalid argument error',
        '202': 'Element cannot have children',
        '203': 'Element not an array - Cannot have count',
        '301': 'Not initialized',
        '401': 'Not implemented error',
        '402': 'Invalid set value, element is a keyword',
        '403': 'Element is read only',
        '404': 'Element is write only',
        '405': 'Incorrect data type'
    };
    
    // SCORM 2004 Error codes
    const errors2004 = {
        '0': 'No Error',
        '101': 'General Exception',
        '102': 'General Initialization Failure',
        '103': 'Already Initialized',
        '104': 'Content Instance Terminated',
        '111': 'General Termination Failure',
        '112': 'Termination Before Initialization',
        '113': 'Termination After Termination',
        '122': 'Retrieve Data Before Initialization',
        '123': 'Retrieve Data After Termination',
        '132': 'Store Data Before Initialization',
        '133': 'Store Data After Termination',
        '142': 'Commit Before Initialization',
        '143': 'Commit After Termination',
        '201': 'General Argument Error',
        '301': 'General Get Failure',
        '351': 'General Set Failure',
        '391': 'General Commit Failure',
        '401': 'Undefined Data Model Element',
        '402': 'Unimplemented Data Model Element',
        '403': 'Data Model Element Value Not Initialized',
        '404': 'Data Model Element Is Read Only',
        '405': 'Data Model Element Is Write Only',
        '406': 'Data Model Element Type Mismatch',
        '407': 'Data Model Element Value Out Of Range',
        '408': 'Data Model Dependency Not Established'
    };
    
    // ===================
    // SCORM 1.2 API
    // ===================
    window.API = {
        LMSInitialize: function(param) {
            window.__SCORM__.version = '1.2';
            window.__SCORM__.initialized = true;
            window.__SCORM__.data = {...cmiData12};
            window.__SCORM__.lastError = '0';
            return logCall('1.2', 'LMSInitialize', arguments, 'true');
        },
        
        LMSFinish: function(param) {
            window.__SCORM__.terminated = true;
            window.__SCORM__.lastError = '0';
            return logCall('1.2', 'LMSFinish', arguments, 'true');
        },
        
        LMSGetValue: function(element) {
            if (!window.__SCORM__.initialized) {
                window.__SCORM__.lastError = '301';
                return logCall('1.2', 'LMSGetValue', arguments, '');
            }
            
            let value = window.__SCORM__.data[element];
            
            // Handle _count for arrays
            if (element.endsWith('._count')) {
                value = value || '0';
            }
            
            // Handle _children
            if (element.endsWith('._children')) {
                const parent = element.replace('._children', '');
                if (parent === 'cmi.core') {
                    value = 'student_id,student_name,lesson_location,credit,lesson_status,entry,score,total_time,lesson_mode,exit,session_time';
                } else if (parent === 'cmi.core.score') {
                    value = 'raw,min,max';
                }
            }
            
            window.__SCORM__.lastError = '0';
            return logCall('1.2', 'LMSGetValue', arguments, value || '');
        },
        
        LMSSetValue: function(element, value) {
            if (!window.__SCORM__.initialized) {
                window.__SCORM__.lastError = '301';
                return logCall('1.2', 'LMSSetValue', arguments, 'false');
            }
            
            // Handle array elements (objectives, interactions)
            if (element.includes('objectives.') || element.includes('interactions.')) {
                const match = element.match(/\d+/);
                if (match) {
                    const index = parseInt(match[0]);
                    const countKey = element.split('.').slice(0, 2).join('.') + '._count';
                    const currentCount = parseInt(window.__SCORM__.data[countKey] || '0');
                    if (index >= currentCount) {
                        window.__SCORM__.data[countKey] = String(index + 1);
                    }
                }
            }
            
            window.__SCORM__.data[element] = value;
            window.__SCORM__.lastError = '0';
            return logCall('1.2', 'LMSSetValue', arguments, 'true');
        },
        
        LMSCommit: function(param) {
            window.__SCORM__.lastError = '0';
            return logCall('1.2', 'LMSCommit', arguments, 'true');
        },
        
        LMSGetLastError: function() {
            return logCall('1.2', 'LMSGetLastError', arguments, window.__SCORM__.lastError);
        },
        
        LMSGetErrorString: function(errorCode) {
            const msg = errors12[errorCode] || 'Unknown error';
            return logCall('1.2', 'LMSGetErrorString', arguments, msg);
        },
        
        LMSGetDiagnostic: function(errorCode) {
            const msg = errors12[errorCode] || 'No diagnostic available';
            return logCall('1.2', 'LMSGetDiagnostic', arguments, msg);
        }
    };
    
    // ===================
    // SCORM 2004 API
    // ===================
    window.API_1484_11 = {
        Initialize: function(param) {
            window.__SCORM__.version = '2004';
            window.__SCORM__.initialized = true;
            window.__SCORM__.data = {...cmiData2004};
            window.__SCORM__.lastError = '0';
            return logCall('2004', 'Initialize', arguments, 'true');
        },
        
        Terminate: function(param) {
            window.__SCORM__.terminated = true;
            window.__SCORM__.lastError = '0';
            return logCall('2004', 'Terminate', arguments, 'true');
        },
        
        GetValue: function(element) {
            if (!window.__SCORM__.initialized) {
                window.__SCORM__.lastError = '122';
                return logCall('2004', 'GetValue', arguments, '');
            }
            
            let value = window.__SCORM__.data[element];
            
            // Handle _count
            if (element.endsWith('._count')) {
                value = value || '0';
            }
            
            // Handle _children
            if (element.endsWith('._children')) {
                const parent = element.replace('._children', '');
                if (parent === 'cmi') {
                    value = 'learner_id,learner_name,location,credit,completion_status,success_status,entry,score,total_time,mode,exit,session_time,suspend_data,launch_data,objectives,interactions,comments_from_learner,comments_from_lms,learner_preference,progress_measure,scaled_passing_score';
                } else if (parent === 'cmi.score') {
                    value = 'raw,min,max,scaled';
                }
            }
            
            // Handle cmi._version
            if (element === 'cmi._version') {
                value = '1.0';
            }
            
            window.__SCORM__.lastError = '0';
            return logCall('2004', 'GetValue', arguments, value || '');
        },
        
        SetValue: function(element, value) {
            if (!window.__SCORM__.initialized) {
                window.__SCORM__.lastError = '132';
                return logCall('2004', 'SetValue', arguments, 'false');
            }
            
            // Handle array elements
            if (element.includes('objectives.') || element.includes('interactions.') || 
                element.includes('comments_from_learner.')) {
                const match = element.match(/\d+/);
                if (match) {
                    const index = parseInt(match[0]);
                    const parts = element.split('.');
                    const countKey = parts.slice(0, 2).join('.') + '._count';
                    const currentCount = parseInt(window.__SCORM__.data[countKey] || '0');
                    if (index >= currentCount) {
                        window.__SCORM__.data[countKey] = String(index + 1);
                    }
                }
            }
            
            window.__SCORM__.data[element] = value;
            window.__SCORM__.lastError = '0';
            return logCall('2004', 'SetValue', arguments, 'true');
        },
        
        Commit: function(param) {
            window.__SCORM__.lastError = '0';
            return logCall('2004', 'Commit', arguments, 'true');
        },
        
        GetLastError: function() {
            return logCall('2004', 'GetLastError', arguments, window.__SCORM__.lastError);
        },
        
        GetErrorString: function(errorCode) {
            const msg = errors2004[errorCode] || 'Unknown error';
            return logCall('2004', 'GetErrorString', arguments, msg);
        },
        
        GetDiagnostic: function(errorCode) {
            const msg = errors2004[errorCode] || 'No diagnostic available';
            return logCall('2004', 'GetDiagnostic', arguments, msg);
        }
    };
    
    // Helper functions exposed globally for testing
    window.__SCORM__.getSummary = function() {
        return {
            version: window.__SCORM__.version,
            initialized: window.__SCORM__.initialized,
            terminated: window.__SCORM__.terminated,
            totalCalls: window.__SCORM__.calls.length,
            data: window.__SCORM__.data,
            errors: window.__SCORM__.errors
        };
    };
    
    window.__SCORM__.getCallsByMethod = function(method) {
        return window.__SCORM__.calls.filter(c => c.method === method);
    };
    
    window.__SCORM__.reset = function() {
        window.__SCORM__.initialized = false;
        window.__SCORM__.terminated = false;
        window.__SCORM__.calls = [];
        window.__SCORM__.errors = [];
        window.__SCORM__.lastError = '0';
        window.__SCORM__.startTime = Date.now();
    };
    
    console.log('[SCORM Stub] Initialized - window.API (1.2) and window.API_1484_11 (2004) available');
})();
