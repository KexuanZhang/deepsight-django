/**
 * UI Configuration constants for the notebook feature
 * Centralizes styling, animations, and UI behavior settings
 */

// Layout configurations
export const LAYOUT_RATIOS = {
  sources: 3,    // 3fr for sources panel
  chat: 6.5,     // 6.5fr for chat panel  
  studio: 4.5    // 4.5fr for studio panel
};

// Animation configurations
export const ANIMATIONS = {
  duration: {
    fast: 0.2,
    normal: 0.3,
    slow: 0.5
  },
  easing: {
    easeOut: "easeOut",
    easeIn: "easeIn",
    spring: "spring"
  },
  delays: {
    suggestion: 0.4,
    suggestionItem: 0.08,
    stagger: 0.05
  }
};

// Color themes - Unified color system for deepdive pages
export const COLORS = {
  // Main theme colors (red-based for deepdive consistency)
  theme: {
    primary: {
      50: '#fef2f2',   // bg-red-50
      100: '#fee2e2',  // bg-red-100
      200: '#fecaca',  // bg-red-200
      300: '#fca5a5',  // bg-red-300
      400: '#f87171',  // bg-red-400
      500: '#ef4444',  // bg-red-500
      600: '#dc2626',  // bg-red-600 (main brand)
      700: '#b91c1c',  // bg-red-700
      800: '#991b1b',  // bg-red-800
      900: '#7f1d1d'   // bg-red-900
    },
    secondary: {
      50: '#f9fafb',   // bg-gray-50
      100: '#f3f4f6',  // bg-gray-100
      200: '#e5e7eb',  // bg-gray-200
      300: '#d1d5db',  // bg-gray-300
      400: '#9ca3af',  // bg-gray-400
      500: '#6b7280',  // bg-gray-500
      600: '#4b5563',  // bg-gray-600
      700: '#374151',  // bg-gray-700
      800: '#1f2937',  // bg-gray-800
      900: '#111827'   // bg-gray-900
    },
    success: {
      400: '#4ade80',  // bg-green-400
      500: '#22c55e',  // bg-green-500
      600: '#16a34a'   // bg-green-600
    },
    warning: {
      400: '#facc15',  // bg-yellow-400
      500: '#eab308',  // bg-yellow-500
      600: '#ca8a04'   // bg-yellow-600
    },
    error: {
      400: '#f87171',  // bg-red-400
      500: '#ef4444',  // bg-red-500
      600: '#dc2626'   // bg-red-600
    }
  },
  
  // Tailwind class shortcuts for convenience
  tw: {
    primary: {
      bg: {
        50: 'bg-red-50',
        100: 'bg-red-100',
        200: 'bg-red-200',
        300: 'bg-red-300',
        400: 'bg-red-400',
        500: 'bg-red-500',
        600: 'bg-red-600',
        700: 'bg-red-700',
        800: 'bg-red-800',
        900: 'bg-red-900'
      },
      text: {
        50: 'text-red-50',
        100: 'text-red-100',
        200: 'text-red-200',
        300: 'text-red-300',
        400: 'text-red-400',
        500: 'text-red-500',
        600: 'text-red-600',
        700: 'text-red-700',
        800: 'text-red-800',
        900: 'text-red-900'
      },
      border: {
        200: 'border-red-200',
        300: 'border-red-300',
        400: 'border-red-400',
        500: 'border-red-500',
        600: 'border-red-600'
      },
      hover: {
        bg: {
          600: 'hover:bg-red-600',
          700: 'hover:bg-red-700'
        },
        text: {
          600: 'hover:text-red-600',
          700: 'hover:text-red-700'
        },
        border: {
          300: 'hover:border-red-300',
          400: 'hover:border-red-400'
        }
      }
    },
    secondary: {
      bg: {
        50: 'bg-gray-50',
        100: 'bg-gray-100',
        200: 'bg-gray-200',
        700: 'bg-gray-700',
        800: 'bg-gray-800',
        900: 'bg-gray-900'
      },
      text: {
        400: 'text-gray-400',
        500: 'text-gray-500',
        600: 'text-gray-600',
        700: 'text-gray-700',
        800: 'text-gray-800',
        900: 'text-gray-900'
      },
      border: {
        200: 'border-gray-200',
        300: 'border-gray-300',
        400: 'border-gray-400'
      }
    }
  },
  
  // Component-specific color schemes
  components: {
    button: {
      primary: 'bg-red-600 hover:bg-red-700 text-white',
      secondary: 'bg-gray-100 text-gray-700 hover:bg-gray-200',
      outline: 'border border-red-600 text-red-600 hover:bg-red-50'
    },
    modal: {
      background: 'bg-white',
      overlay: 'bg-black/50',
      header: 'bg-gray-50',
      border: 'border-gray-200'
    },
    form: {
      input: 'bg-gray-50 border-gray-300 focus:ring-2 focus:ring-red-500 focus:border-transparent',
      label: 'text-gray-700',
      error: 'text-red-600'
    },
    notification: {
      success: 'bg-gray-50 border-green-200 text-green-800',
      error: 'bg-red-50 border-red-200 text-red-800',
      warning: 'bg-yellow-50 border-yellow-200 text-yellow-800',
      info: 'bg-gray-50 border-gray-200 text-gray-800'
    }
  },
  
  // Panel-specific color schemes
  panels: {
    // Common background for all panels
    commonBackground: 'bg-white',
    sources: {
      background: 'bg-white',
      ring: '',
      text: 'text-gray-700',
      textHover: 'text-gray-800'
    },
    chat: {
      background: 'bg-white',
      ring: '',
      text: 'text-gray-700',
      textHover: 'text-gray-800'
    },
    studio: {
      background: 'bg-white',
      ring: '',
      text: 'text-gray-700',
      textHover: 'text-gray-800'
    }
  },
  
  // Legacy support (for backward compatibility)
  primary: {
    50: 'from-red-50',
    100: 'bg-red-100',
    500: 'bg-red-500',
    600: 'bg-red-600',
    700: 'bg-red-700'
  },
  secondary: {
    50: 'from-gray-50',
    100: 'bg-gray-100',
    500: 'bg-gray-500',
    600: 'bg-gray-600',
    700: 'bg-gray-700'
  },
  accent: {
    purple: {
      500: 'bg-purple-500',
      600: 'bg-purple-600'
    },
    red: {
      500: 'bg-red-500',
      600: 'bg-red-600'
    },
    green: {
      500: 'bg-green-500',
      600: 'bg-green-600'
    }
  }
};

// Spacing configurations
export const SPACING = {
  panel: {
    padding: 'p-4',
    margin: 'm-4',
    gap: 'gap-4'
  },
  component: {
    padding: 'p-6',
    margin: 'm-6',
    gap: 'gap-6'
  },
  item: {
    padding: 'p-3',
    margin: 'm-3',
    gap: 'gap-3'
  }
};

// Typography configurations
export const TYPOGRAPHY = {
  heading: {
    h1: 'text-3xl font-bold',
    h2: 'text-2xl font-semibold',
    h3: 'text-xl font-medium',
    h4: 'text-lg font-medium'
  },
  body: {
    large: 'text-base',
    normal: 'text-sm',
    small: 'text-xs'
  },
  weight: {
    light: 'font-light',
    normal: 'font-normal',
    medium: 'font-medium',
    semibold: 'font-semibold',
    bold: 'font-bold'
  }
};

// Panel header configurations for consistency
export const PANEL_HEADERS = {
  container: 'flex-shrink-0 px-6 py-4 bg-gray-100/95 backdrop-blur-sm',
  separator: '',
  layout: 'flex items-center justify-between',
  iconContainer: 'w-8 h-8 bg-gradient-to-br from-gray-100 to-gray-200 rounded-xl flex items-center justify-center shadow-sm',
  icon: 'h-4 w-4 text-gray-600',
  title: 'text-lg font-semibold text-gray-900',
  titleContainer: 'flex items-center space-x-4',
  actionsContainer: 'flex items-center space-x-2'
};

// Border radius configurations
export const RADIUS = {
  small: 'rounded-md',
  normal: 'rounded-lg',
  large: 'rounded-xl',
  full: 'rounded-full'
};

// Shadow configurations
export const SHADOWS = {
  small: 'shadow-sm',
  normal: 'shadow-md',
  large: 'shadow-lg',
  xl: 'shadow-xl',
  // Enhanced panel shadows
  panel: {
    base: 'shadow-lg',
    hover: 'hover:shadow-xl',
    elevated: 'shadow-xl shadow-blue-100/20'
  }
};

// Z-index configurations
export const Z_INDEX = {
  modal: 'z-[100]',
  overlay: 'z-[90]',
  dropdown: 'z-[80]',
  header: 'z-10'
};

// Responsive breakpoints
export const BREAKPOINTS = {
  sm: 'sm:',
  md: 'md:',
  lg: 'lg:',
  xl: 'xl:',
  '2xl': '2xl:'
};

// Responsive panel configurations
export const RESPONSIVE_PANELS = {
  mobile: {
    gap: 'gap-3',
    padding: 'px-3 pb-3 pt-1',
    radius: 'rounded-xl'
  },
  tablet: {
    gap: 'gap-4',
    padding: 'px-4 pb-4 pt-2',
    radius: 'rounded-xl'
  },
  desktop: {
    gap: 'gap-5',
    padding: 'px-5 pb-5 pt-2',
    radius: 'rounded-2xl'
  }
};

// Component size configurations
export const SIZES = {
  icon: {
    small: 'h-4 w-4',
    normal: 'h-5 w-5',
    large: 'h-6 w-6',
    xl: 'h-8 w-8'
  },
  button: {
    small: 'h-8 px-3 text-xs',
    normal: 'h-10 px-4 text-sm',
    large: 'h-12 px-6 text-base'
  },
  input: {
    small: 'h-8 px-3 text-xs',
    normal: 'h-10 px-3 text-sm',
    large: 'h-12 px-4 text-base'
  }
};

// Grid configurations
export const GRID = {
  cols: {
    1: 'grid-cols-1',
    2: 'grid-cols-2',
    3: 'grid-cols-3',
    4: 'grid-cols-4',
    responsive: 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4'
  },
  gap: {
    small: 'gap-2',
    normal: 'gap-4',
    large: 'gap-6'
  }
};

// Transition configurations
export const TRANSITIONS = {
  all: 'transition-all',
  colors: 'transition-colors',
  transform: 'transition-transform',
  opacity: 'transition-opacity',
  duration: {
    fast: 'duration-200',
    normal: 'duration-300',
    slow: 'duration-500'
  }
};

// State configurations
export const STATES = {
  hover: {
    scale: 'hover:scale-105',
    bg: 'hover:bg-gray-50',
    text: 'hover:text-blue-600'
  },
  focus: {
    ring: 'focus:ring-2 focus:ring-blue-500',
    outline: 'focus:outline-none'
  },
  active: {
    scale: 'active:scale-95',
    bg: 'active:bg-blue-700'
  },
  disabled: {
    opacity: 'disabled:opacity-50',
    cursor: 'disabled:cursor-not-allowed'
  }
};

// Layout utility functions
export const buildGridCols = (count: number): string => {
  const colMap: Record<number, string> = {
    1: 'grid-cols-1',
    2: 'grid-cols-2',
    3: 'grid-cols-3',
    4: 'grid-cols-4',
    5: 'grid-cols-5',
    6: 'grid-cols-6'
  };
  return colMap[count] || 'grid-cols-1';
};

export const buildSpacing = (size: 'xs' | 'sm' | 'md' | 'lg' | 'xl'): string => {
  const sizeMap: Record<string, string> = {
    xs: 'gap-1 p-1',
    sm: 'gap-2 p-2',
    md: 'gap-4 p-4',
    lg: 'gap-6 p-6',
    xl: 'gap-8 p-8'
  };
  return sizeMap[size] || sizeMap.md || 'gap-4 p-4';
};