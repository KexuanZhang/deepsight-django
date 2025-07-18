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

// Color themes
export const COLORS = {
  primary: {
    50: 'from-blue-50',
    100: 'bg-blue-100',
    500: 'bg-blue-500',
    600: 'bg-blue-600',
    700: 'bg-blue-700'
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
  },
  // Panel-specific color schemes
  panels: {
    sources: {
      background: 'bg-gradient-to-b from-emerald-50 to-teal-50/50',
      ring: 'ring-emerald-100/50',
      text: 'text-emerald-600',
      textHover: 'hover:text-emerald-700'
    },
    chat: {
      background: 'bg-gradient-to-b from-blue-50 to-indigo-50/50',
      ring: 'ring-blue-100/50',
      text: 'text-blue-600',
      textHover: 'hover:text-blue-700'
    },
    studio: {
      background: 'bg-gradient-to-b from-purple-50 to-pink-50/50',
      ring: 'ring-purple-100/50',
      text: 'text-purple-600',
      textHover: 'hover:text-purple-700'
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
  modal: 'z-50',
  overlay: 'z-40',
  dropdown: 'z-30',
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
    padding: 'p-3',
    radius: 'rounded-xl'
  },
  tablet: {
    gap: 'gap-4',
    padding: 'p-4',
    radius: 'rounded-xl'
  },
  desktop: {
    gap: 'gap-6',
    padding: 'p-6',
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
export const buildGridCols = (count) => {
  const colMap = {
    1: 'grid-cols-1',
    2: 'grid-cols-2',
    3: 'grid-cols-3',
    4: 'grid-cols-4',
    5: 'grid-cols-5',
    6: 'grid-cols-6'
  };
  return colMap[count] || 'grid-cols-1';
};

export const buildSpacing = (size) => {
  const sizeMap = {
    xs: 'gap-1 p-1',
    sm: 'gap-2 p-2',
    md: 'gap-4 p-4',
    lg: 'gap-6 p-6',
    xl: 'gap-8 p-8'
  };
  return sizeMap[size] || sizeMap.md;
};