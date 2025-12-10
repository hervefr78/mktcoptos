const theme = {
  colors: {
    primary: '#4a90e2',
    secondary: '#50e3c2',
    background: '#f5f5f5',
    text: '#333333',
  },
  typography: {
    base: "'Helvetica Neue', Arial, sans-serif",
    heading: "'Roboto', sans-serif",
    size: '16px',
  },
  spacing: {
    xs: '4px',
    sm: '8px',
    md: '16px',
    lg: '24px',
    xl: '32px',
  },
};

export const applyTheme = (t = theme) => {
  const root = document.documentElement;
  Object.entries(t.colors).forEach(([key, value]) =>
    root.style.setProperty(`--color-${key}`, value)
  );
  Object.entries(t.typography).forEach(([key, value]) =>
    root.style.setProperty(`--font-${key}`, value)
  );
  Object.entries(t.spacing).forEach(([key, value]) =>
    root.style.setProperty(`--spacing-${key}`, value)
  );
};

export default theme;
