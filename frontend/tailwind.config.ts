import type { Config } from 'tailwindcss'

const config: Config = {
  content: ['./src/**/*.{js,ts,jsx,tsx,mdx}'],
  theme: {
    extend: {
      colors: {
        ink: '#172026',
        steel: '#53636f',
        mist: '#eef3f6',
        line: '#d7e0e5',
        accent: '#0f766e',
        amber: '#b45309',
        danger: '#b91c1c',
      },
      boxShadow: {
        soft: '0 14px 40px rgba(23, 32, 38, 0.08)',
      },
    },
  },
  plugins: [],
}

export default config

