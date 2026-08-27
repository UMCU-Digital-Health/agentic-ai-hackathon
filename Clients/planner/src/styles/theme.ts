import { createTheme } from '@mantine/core'

/**
 * The UMC Utrecht palette, declared once. Everything downstream — Mantine
 * components, our CSS Modules, the FullCalendar overrides — reads
 * `var(--mantine-color-*)`, so no component ever references a hex.
 */
export const theme = createTheme({
  primaryColor: 'umcBlue',
  primaryShade: 6,
  fontFamily: 'system-ui, "Segoe UI", Roboto, sans-serif',
  defaultRadius: 'md',
  radius: { sm: '6px', md: '10px', lg: '16px' },
  colors: {
    // index 6 is the sampled brand colour
    umcBlue: [
      '#eef7ff', '#d9ecfe', '#b0d7fd', '#84c1fc', '#5faefa',
      '#3d9df7', '#298ff5', '#1a7ade', '#0d6bc6', '#005aae',
    ],
    umcOrange: [
      '#fff0ec', '#ffe0d8', '#ffc0b0', '#ff9e84', '#fe8160',
      '#fd6f4a', '#fb6944', '#e05635', '#c8492b', '#ae3b20',
    ],
    umcIndigo: [
      '#ecebfd', '#d5d3fa', '#a9a4f4', '#7c74ee', '#5a50e9',
      '#443ae6', '#3a2fe5', '#2f24cb', '#2b20d0', '#221a9f',
    ],
  },
})
