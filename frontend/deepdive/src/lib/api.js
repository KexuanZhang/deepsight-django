// // const API_BASE_URL = 'http://localhost:8000/api/notebooks';

// // class ApiService {
// //   constructor() {
// //     this.baseUrl = API_BASE_URL;
// //   }

// //   async request(endpoint, options = {}) {
// //     const url = `${endpoint.startsWith('http') ? '' : this.baseUrl}${endpoint}`;
// //     const config = {
// //       headers: {
// //         'Content-Type': 'application/json',
// //         ...options.headers,
// //       },
// //       ...options,
// //     };

// //     try {
// //       const response = await fetch(url, config);
// //       if (!response.ok) {
// //         let errorMessage = `HTTP error! status: ${response.status}`;
// //         try {
// //           const errorData = await response.json();
// //           if (errorData.detail) {
// //             if (Array.isArray(errorData.detail)) {
// //               const validationErrors = errorData.detail
// //                 .map(err => `${err.loc?.join('.')} - ${err.msg}`)
// //                 .join('; ');
// //               errorMessage = `Validation error: ${validationErrors}`;
// //             } else {
// //               errorMessage = errorData.detail;
// //             }
// //           }
// //         } catch {
// //           // ignore JSON parse errors
// //         }
// //         throw new Error(errorMessage);
// //       }
// //       return await response.json();
// //     } catch (error) {
// //       console.error('API request failed:', error);
// //       throw error;
// //     }
// //   }

// //   // ===== NOTEBOOK FILES =====

// //   /**
// //    * List all files for a notebook
// //    * GET /notebooks/{notebookId}/files/
// //    */
// //   async listParsedFiles(notebookId) {
// //     return this.request(`/${notebookId}/files/`);
// //   }

// //   /**
// //    * Upload & parse a file for a notebook
// //    * POST /notebooks/{notebookId}/files/upload/
// //    */
// //   async parseFile(file, uploadFileId = null, notebookId) {
// //     const formData = new FormData();
// //     formData.append('file', file);
// //     formData.append('notebook', notebookId);
// //     if (uploadFileId) {
// //       formData.append('upload_file_id', uploadFileId);
// //     }

// //     return this.request(
// //       `/${notebookId}/files/upload/`,
// //       {
// //         method: 'POST',
// //         headers: {}, // browser will set Content-Type for FormData
// //         body: formData,
// //       }
// //     );
// //   }

// //   /**
// //    * Delete a completed (parsed) file
// //    * DELETE /notebooks/{notebookId}/files/{fileId}/
// //    */
// //   async deleteParsedFile(fileId, notebookId) {
// //     return this.request(
// //       `/${notebookId}/files/${fileId}/`,
// //       { method: 'DELETE' }
// //     );
// //   }

// //   /**
// //    * Delete an in-progress upload by upload_file_id
// //    * DELETE /notebooks/{notebookId}/files/{uploadFileId}/
// //    */
// //   async deleteFileByUploadId(uploadFileId, notebookId) {
// //     return this.request(
// //       `/${notebookId}/files/${uploadFileId}/`,
// //       { method: 'DELETE' }
// //     );
// //   }

// //   /**
// //    * Get parsing status snapshot
// //    * GET /notebooks/{notebookId}/files/{uploadFileId}/status/
// //    */
// //   async getParsingStatus(uploadFileId, notebookId) {
// //     return this.request(`/${notebookId}/files/${uploadFileId}/status/`);
// //   }

// //   /**
// //    * SSE stream for real-time parsing updates
// //    * EventSource → http://localhost:8000/notebooks/{notebookId}/files/{uploadFileId}/status/
// //    */
// //   createParsingStatusStream(uploadFileId, onMessage, onError = null, onClose = null, notebookId) {
// //     const url = `http://localhost:8000/notebooks/${notebookId}/files/${uploadFileId}/status/`;
// //     const es  = new EventSource(url, { withCredentials: true });

// //     es.onmessage = (e) => {
// //       try {
// //         onMessage(JSON.parse(e.data));
// //       } catch (err) {
// //         console.error('Error parsing SSE data:', err);
// //         onError?.(err);
// //       }
// //     };

// //     es.onerror = (err) => {
// //       console.error('SSE error:', err);
// //       onError?.(err);
// //     };

// //     // some browsers don’t fire onclose — you can detect with readyState
// //     es.onclose = () => onClose?.();

// //     return es;
// //   }
// // }

// // const apiService = new ApiService();
// // export default apiService;

// const API_BASE_URL = 'http://localhost:8000/api/notebooks';

// class ApiService {
//   constructor() {
//     this.baseUrl = API_BASE_URL;
//   }

//   async request(endpoint, options = {}) {
//     const url = endpoint.startsWith('http') 
//       ? endpoint 
//       : `${this.baseUrl}${endpoint}`;
//     const config = {
//       headers: {
//         'Content-Type': 'application/json',
//         ...options.headers,
//       },
//       ...options,
//     };

//     try {
//       const response = await fetch(url, config);
//       if (!response.ok) {
//         let msg = `HTTP ${response.status}`;
//         try {
//           const err = await response.json();
//           if (err.detail) {
//             if (Array.isArray(err.detail)) {
//               msg = err.detail.map(d => `${d.loc.join('.')} – ${d.msg}`).join('; ');
//             } else {
//               msg = err.detail;
//             }
//           }
//         } catch {}
//         throw new Error(msg);
//       }
//       return await response.json();
//     } catch (e) {
//       console.error('API request failed:', e);
//       throw e;
//     }
//   }

//   // ─── FILES ────────────────────────────────────────────────────────────────

//   /**
//    * List all parsed files in a notebook
//    * GET /api/notebooks/{notebookId}/files/
//    */
//   async listFiles(notebookId, { limit = 50, offset = 0 } = {}) {
//     return this.request(`/${notebookId}/files/?limit=${limit}&offset=${offset}`);
//   }

//   /**
//    * Upload & parse a file
//    * POST /api/notebooks/{notebookId}/files/upload/
//    */
//   async paFile(file, uploadFileId, notebookId) {
//     const form = new FormData();
//     form.append('file', file);
//     form.append('notebook', notebookId);
//     if (uploadFileId) form.append('upload_file_id', uploadFileId);

//     return this.request(
//       `/${notebookId}/files/upload/`,
//       { method: 'POST', headers: {}, body: form }
//     );
//   }

//   /**
//    * Delete a stored file
//    * DELETE /api/notebooks/{notebookId}/files/{fileId}/
//    */
//   async deleteFile(fileId, notebookId) {
//     return this.request(`/${notebookId}/files/${fileId}/`, { method: 'DELETE' });
//   }

//   /**
//    * Cancel or delete an in-progress upload
//    * DELETE /api/notebooks/{notebookId}/files/{uploadFileId}/
//    */
//   async deleteUpload(uploadFileId, notebookId) {
//     return this.request(`/${notebookId}/files/${uploadFileId}/`, { method: 'DELETE' });
//   }

//   // ─── STATUS ───────────────────────────────────────────────────────────────

//   /**
//    * One-off status check
//    * GET /api/notebooks/{notebookId}/files/{uploadFileId}/status/
//    */
//   async getStatus(uploadFileId, notebookId) {
//     return this.request(`/${notebookId}/files/${uploadFileId}/status/`);
//   }

//   /**
//    * SSE stream for live updates
//    * GET /api/notebooks/{notebookId}/files/{uploadFileId}/status/stream
//    */
//   createStatusStream(uploadFileId, notebookId, onMessage, onError, onClose) {
//     const url = `${this.baseUrl}/${notebookId}/files/${uploadFileId}/status/stream`;
//     const es  = new EventSource(url);

//     es.onmessage = e => {
//       try { onMessage(JSON.parse(e.data)); }
//       catch(err) { console.error('SSE parse error', err); onError?.(err); }
//     };
//     es.onerror = err => {
//       console.error('SSE error', err);
//       onError?.(err);
//       es.close();
//       onClose?.();
//     };
//     return es;
//   }
// }

// const apiService = new ApiService();
// export default apiService;

const API_BASE_URL = 'http://localhost:8000/api/notebooks';

// Helper to get CSRF token from cookie
function getCookie(name) {
  const match = document.cookie.match(new RegExp(`(^| )${name}=([^;]+)`));
  return match ? decodeURIComponent(match[2]) : null;
}

class ApiService {
  constructor() {
    this.baseUrl = API_BASE_URL;
  }

  async request(endpoint, options = {}) {
    const url = endpoint.startsWith('http')
      ? endpoint
      : `${this.baseUrl}${endpoint}`;

    const config = {
      credentials: 'include',
      // if we're sending FormData, let the browser set Content-Type for us
      headers: options.body instanceof FormData
        ? { ...options.headers }
        : { 'Content-Type': 'application/json', ...options.headers },
      ...options,
    };

    try {
      const response = await fetch(url, config);
      if (!response.ok) {
        let msg = `HTTP ${response.status}`;
        try {
          const err = await response.json();
          if (err.detail) {
            if (Array.isArray(err.detail)) {
              msg = err.detail.map(d => `${d.loc.join('.')} – ${d.msg}`).join('; ');
            } else {
              msg = err.detail;
            }
          }
        } catch {}
        throw new Error(msg);
      }
      return await response.json();
    } catch (e) {
      console.error('API request failed:', e);
      throw e;
    }
  }

  // ─── FILES ────────────────────────────────────────────────────────────────

  async listFiles(notebookId, { limit = 50, offset = 0 } = {}) {
    return this.request(`/${notebookId}/files/?limit=${limit}&offset=${offset}`);
  }

  async parseFile(file, uploadFileId, notebookId) {
    const form = new FormData();
    form.append('file', file);
    form.append('notebook', notebookId);
    if (uploadFileId) form.append('upload_file_id', uploadFileId);

    return this.request(
      `/${notebookId}/files/upload/`,
      { method: 'POST', headers: {}, body: form, credentials: 'include' }
    );
  }

  createParsingStatusStream(uploadFileId, notebookId, onMessage, onError, onClose) {
    const url = `${this.baseUrl}/${notebookId}/files/${uploadFileId}/status/stream`;
    const es  = new EventSource(url, { withCredentials: true });
    // …
  }

  async deleteFile(fileId, notebookId) {
    return this.request(`/${notebookId}/files/${fileId}/`, {
      method: 'DELETE',
      headers: {
        'X-CSRFToken': getCookie('csrftoken'),
      },
    });
  }

  async deleteUpload(uploadFileId, notebookId) {
    return this.deleteFile(uploadFileId, notebookId); // same as deleteFile
  }

  // ─── STATUS ───────────────────────────────────────────────────────────────

  async getStatus(uploadFileId, notebookId) {
    return this.request(`/${notebookId}/files/${uploadFileId}/status/`);
  }

  createStatusStream(uploadFileId, notebookId, onMessage, onError, onClose) {
    const url = `${this.baseUrl}/${notebookId}/files/${uploadFileId}/status/stream`;
    const es = new EventSource(url, { withCredentials: true }); // include session

    es.onmessage = e => {
      try {
        onMessage(JSON.parse(e.data));
      } catch (err) {
        console.error('SSE parse error', err);
        onError?.(err);
      }
    };
    es.onerror = err => {
      console.error('SSE error', err);
      onError?.(err);
      es.close();
      onClose?.();
    };
    return es;
  }
}

const apiService = new ApiService();
export default apiService;
