/** @type {import('tailwindcss').Config} */
module.exports = {
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
			borderRadius: {
				lg: 'var(--radius)',
				md: 'calc(var(--radius) - 2px)',
				sm: 'calc(var(--radius) - 4px)',
			},
			keyframes: {
				'accordion-down': {
					from: { height: 0 },
					to: { height: 'var(--radix-accordion-content-height)' },
				},
				'accordion-up': {
					from: { height: 'var(--radix-accordion-content-height)' },
					to: { height: 0 },
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
		function({ addUtilities }) {
			addUtilities({
				'.scrollbar-hide': {
					/* IE and Edge */
					'-ms-overflow-style': 'none',
					/* Firefox */
					'scrollbar-width': 'none',
					/* Safari and Chrome */
					'&::-webkit-scrollbar': {
						display: 'none'
					}
				},
				'.scrollbar-beautiful': {
					/* Firefox */
					'scrollbar-width': 'thin',
					'scrollbar-color': 'rgba(239, 68, 68, 0.3) transparent',
					
					/* Webkit browsers */
					'&::-webkit-scrollbar': {
						width: '6px'
					},
					'&::-webkit-scrollbar-track': {
						background: 'transparent',
						borderRadius: '10px'
					},
					'&::-webkit-scrollbar-thumb': {
						background: 'rgba(239, 68, 68, 0.2)',
						borderRadius: '10px',
						border: 'none',
						transition: 'all 0.2s ease'
					},
					'&::-webkit-scrollbar-thumb:hover': {
						background: 'rgba(239, 68, 68, 0.4)'
					},
					'&::-webkit-scrollbar-corner': {
						background: 'transparent'
					}
				},
				'.scrollbar-floating': {
					'scrollbar-width': 'thin',
					'scrollbar-color': 'rgba(239, 68, 68, 0.6) transparent',
					
					'&::-webkit-scrollbar': {
						width: '6px',
						height: '6px'
					},
					'&::-webkit-scrollbar-track': {
						background: 'transparent',
						borderRadius: '12px',
						margin: '4px'
					},
					'&::-webkit-scrollbar-thumb': {
						background: 'linear-gradient(180deg, rgba(239, 68, 68, 0.5) 0%, rgba(220, 38, 38, 0.6) 50%, rgba(239, 68, 68, 0.5) 100%)',
						borderRadius: '12px',
						border: '1px solid rgba(255, 255, 255, 0.4)',
						backgroundClip: 'padding-box',
						boxShadow: '0 2px 6px rgba(239, 68, 68, 0.2), 0 1px 3px rgba(0, 0, 0, 0.1)',
						transition: 'all 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94)'
					},
					'&::-webkit-scrollbar-thumb:hover': {
						background: 'linear-gradient(180deg, rgba(239, 68, 68, 0.7) 0%, rgba(220, 38, 38, 0.8) 50%, rgba(239, 68, 68, 0.7) 100%)',
						boxShadow: '0 3px 8px rgba(239, 68, 68, 0.3), 0 2px 4px rgba(0, 0, 0, 0.15)',
						transform: 'scaleX(1.2)'
					},
					'&::-webkit-scrollbar-thumb:active': {
						background: 'linear-gradient(180deg, rgba(220, 38, 38, 0.8) 0%, rgba(185, 28, 28, 0.9) 50%, rgba(220, 38, 38, 0.8) 100%)'
					},
					'&::-webkit-scrollbar-corner': {
						background: 'transparent'
					}
				},
				'.scrollbar-test': {
					'&::-webkit-scrollbar': {
						width: '12px'
					},
					'&::-webkit-scrollbar-track': {
						background: '#f1f1f1'
					},
					'&::-webkit-scrollbar-thumb': {
						background: '#888'
					},
					'&::-webkit-scrollbar-thumb:hover': {
						background: '#555'
					}
				}
			})
		}
	],
};
