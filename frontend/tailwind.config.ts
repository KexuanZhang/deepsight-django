import type { Config } from 'tailwindcss';

// ============================================================================
// TAILWIND CSS CONFIGURATION
// ============================================================================

const config: Config = {
  darkMode: ['class'],
  
  content: [
    './pages/**/*.{js,jsx,ts,tsx}',
    './components/**/*.{js,jsx,ts,tsx}',
    './app/**/*.{js,jsx,ts,tsx}',
    './src/**/*.{js,jsx,ts,tsx}',
  ],
  
  theme: {
    container: {
      center: true,
      padding: '2rem',
      screens: {
        '2xl': '1400px',
      },
    },
    
    extend: {
      // Color system using CSS custom properties
      colors: {
        border: 'hsl(var(--border))',
        input: 'hsl(var(--input))',
        ring: 'hsl(var(--ring))',
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        primary: {
          DEFAULT: 'hsl(var(--primary))',
          foreground: 'hsl(var(--primary-foreground))',
        },
        secondary: {
          DEFAULT: 'hsl(var(--secondary))',
          foreground: 'hsl(var(--secondary-foreground))',
        },
        destructive: {
          DEFAULT: 'hsl(var(--destructive))',
          foreground: 'hsl(var(--destructive-foreground))',
        },
        muted: {
          DEFAULT: 'hsl(var(--muted))',
          foreground: 'hsl(var(--muted-foreground))',
        },
        accent: {
          DEFAULT: 'hsl(var(--accent))',
          foreground: 'hsl(var(--accent-foreground))',
        },
        popover: {
          DEFAULT: 'hsl(var(--popover))',
          foreground: 'hsl(var(--popover-foreground))',
        },
        card: {
          DEFAULT: 'hsl(var(--card))',
          foreground: 'hsl(var(--card-foreground))',
        },
      },
      
      // Dynamic border radius using CSS variables
      borderRadius: {
        lg: 'var(--radius)',
        md: 'calc(var(--radius) - 2px)',
        sm: 'calc(var(--radius) - 4px)',
      },
      
      // Custom animations for UI components
      keyframes: {
        'accordion-down': {
          from: { height: '0' },
          to: { height: 'var(--radix-accordion-content-height)' },
        },
        'accordion-up': {
          from: { height: 'var(--radix-accordion-content-height)' },
          to: { height: '0' },
        },
      },
      
      animation: {
        'accordion-down': 'accordion-down 0.2s ease-out',
        'accordion-up': 'accordion-up 0.2s ease-out',
      },
    },
  },
  
  plugins: [
    require('tailwindcss-animate'),
    require('@tailwindcss/typography'),
    
    // Custom scrollbar utilities
    function ({ addUtilities }: { addUtilities: (utilities: Record<string, any>) => void }) {
      addUtilities({
        '.scrollbar-hide': {
          // IE and Edge
          '-ms-overflow-style': 'none',
          // Firefox
          'scrollbar-width': 'none',
          // Safari and Chrome
          '&::-webkit-scrollbar': {
            display: 'none',
          },
        },
        
        '.scrollbar-overlay': {
          // Create a thin, unobtrusive scrollbar
          'overflow-y': 'auto',
          'overflow-x': 'hidden',
          
          // Firefox
          'scrollbar-width': 'thin',
          'scrollbar-color': 'rgba(156, 163, 175, 0.3) transparent',
          
          // Webkit browsers
          '&::-webkit-scrollbar': {
            width: '6px',
          },
          '&::-webkit-scrollbar-track': {
            background: 'transparent',
          },
          '&::-webkit-scrollbar-thumb': {
            background: 'rgba(156, 163, 175, 0.3)',
            borderRadius: '2px',
            transition: 'all 0.2s ease',
          },
          '&::-webkit-scrollbar-thumb:hover': {
            background: 'rgba(107, 114, 128, 0.5)',
          },
          '&::-webkit-scrollbar-corner': {
            background: 'transparent',
          },
        },
      });
    },
  ],
};

export default config;
