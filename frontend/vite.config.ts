import path from 'node:path';
import react from '@vitejs/plugin-react';
import { createLogger, defineConfig, type PluginOption } from 'vite';

// ============================================================================
// TYPES
// ============================================================================

interface MessageData {
  type: string;
  error?: string;
  message?: string;
}

// ============================================================================
// ERROR HANDLING SCRIPTS
// ============================================================================

const viteErrorHandler: string = `
const observer = new MutationObserver((mutations) => {
  for (const mutation of mutations) {
    for (const addedNode of mutation.addedNodes) {
      if (
        addedNode.nodeType === Node.ELEMENT_NODE &&
        (
          addedNode.tagName && addedNode.tagName.toLowerCase() === 'vite-error-overlay' ||
          addedNode.classList && addedNode.classList.contains('backdrop')
        )
      ) {
        handleViteOverlay(addedNode);
      }
    }
  }
});

observer.observe(document.documentElement, {
  childList: true,
  subtree: true
});

function handleViteOverlay(node) {
  if (!node.shadowRoot) {
    return;
  }

  const backdrop = node.shadowRoot.querySelector('.backdrop');

  if (backdrop) {
    const overlayHtml = backdrop.outerHTML;
    const parser = new DOMParser();
    const doc = parser.parseFromString(overlayHtml, 'text/html');
    const messageBodyElement = doc.querySelector('.message-body');
    const fileElement = doc.querySelector('.file');
    const messageText = messageBodyElement ? (messageBodyElement.textContent && messageBodyElement.textContent.trim()) || '' : '';
    const fileText = fileElement ? (fileElement.textContent && fileElement.textContent.trim()) || '' : '';
    const error = messageText + (fileText ? ' File:' + fileText : '');

    window.parent.postMessage({
      type: 'horizons-vite-error',
      error: error,
    }, '*');
  }
}
`;

const runtimeErrorHandler: string = `
window.onerror = (message, source, lineno, colno, errorObj) => {
  const errorDetails = errorObj ? JSON.stringify({
    name: errorObj.name,
    message: errorObj.message,
    stack: errorObj.stack,
    source,
    lineno,
    colno,
  }) : null;

  window.parent.postMessage({
    type: 'horizons-runtime-error',
    message,
    error: errorDetails
  }, '*');
  
  return false;
};
`;

const consoleErrorHandler: string = `
const originalConsoleError = console.error;
console.error = function(...args) {
  originalConsoleError.apply(console, args);

  let errorString = '';

  for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    if (arg instanceof Error) {
      errorString = arg.stack || (arg.name + ': ' + arg.message);
      break;
    }
  }

  if (!errorString) {
    errorString = args.map((arg) => 
      typeof arg === 'object' ? JSON.stringify(arg) : String(arg)
    ).join(' ');
  }

  window.parent.postMessage({
    type: 'horizons-console-error',
    error: errorString
  }, '*');
};
`;

const fetchMonkeyPatch: string = `
const originalFetch = window.fetch;

window.fetch = function(...args) {
  const url = args[0] instanceof Request ? args[0].url : args[0];

  // Skip WebSocket URLs
  if (url.startsWith('ws:') || url.startsWith('wss:')) {
    return originalFetch.apply(this, args);
  }

  return originalFetch.apply(this, args)
    .then(async (response) => {
      const contentType = response.headers.get('Content-Type') || '';

      // Exclude HTML document responses
      const isDocumentResponse =
        contentType.includes('text/html') ||
        contentType.includes('application/xhtml+xml');

      if (!response.ok && !isDocumentResponse) {
        const responseClone = response.clone();
        const errorFromRes = await responseClone.text();
        const requestUrl = response.url;
        console.error('Fetch error from ' + requestUrl + ': ' + errorFromRes);
      }

      return response;
    })
    .catch((error) => {
      if (!url.match(/\\.html?$/i)) {
        console.error(error);
      }
      throw error;
    });
};
`;

// ============================================================================
// VITE PLUGINS
// ============================================================================

const addTransformIndexHtml: PluginOption = {
  name: 'add-transform-index-html',
  transformIndexHtml(html: string) {
    return {
      html,
      tags: [
        {
          tag: 'script',
          attrs: { type: 'module' },
          children: runtimeErrorHandler,
          injectTo: 'head',
        },
        {
          tag: 'script',
          attrs: { type: 'module' },
          children: viteErrorHandler,
          injectTo: 'head',
        },
        {
          tag: 'script',
          attrs: { type: 'module' },
          children: consoleErrorHandler,
          injectTo: 'head',
        },
        {
          tag: 'script',
          attrs: { type: 'module' },
          children: fetchMonkeyPatch,
          injectTo: 'head',
        },
      ],
    };
  },
};

// ============================================================================
// LOGGER CONFIGURATION
// ============================================================================

// Suppress console warnings
console.warn = (): void => {};

const logger = createLogger();
const loggerError = logger.error;

logger.error = (msg: string, options?: { error?: Error }): void => {
  if (options?.error?.toString().includes('CssSyntaxError: [postcss]')) {
    return;
  }
  loggerError(msg, options);
};

// ============================================================================
// VITE CONFIGURATION
// ============================================================================

export default defineConfig({
  customLogger: logger,
  
  plugins: [
    react(),
    addTransformIndexHtml,
  ],
  
  server: {
    proxy: {
      '/api': {
        target: process.env.VITE_BACKEND_URL || 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      },
    },
    cors: true,
    headers: {
      'Cross-Origin-Embedder-Policy': 'credentialless',
    },
    allowedHosts: true,
  },
  
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          // Vendor libraries
          react: ['react', 'react-dom'],
          redux: ['@reduxjs/toolkit', 'react-redux', 'redux-persist'],
          query: ['@tanstack/react-query', '@tanstack/react-query-devtools'],
          ui: ['@radix-ui/react-dialog', '@radix-ui/react-dropdown-menu', '@radix-ui/react-toast', '@headlessui/react'],
          table: ['@tanstack/react-table'],
          router: ['react-router-dom'],
          markdown: ['react-markdown', 'rehype-highlight', 'rehype-raw', 'remark-gfm'],
        },
      },
    },
    chunkSizeWarningLimit: 1000,
  },
  
  resolve: {
    extensions: ['.tsx', '.ts', '.jsx', '.js', '.json'],
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
});