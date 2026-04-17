# Aurora 2026 Design System — Reference

This file contains the complete Aurora 2026 design system used by the Premium Wireframe Generator Agent. It includes typography, color tokens, all 12 CSS components, the ambient background system, and the theme toggle implementation.

---

## Design System: "Aurora 2026"

### Typography

```css
/* Primary Font - Clean, Modern, Geometric */
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');

font-family: 'Outfit', -apple-system, BlinkMacSystemFont, sans-serif;

/* Font Scale */
--text-xs: 10px;    /* Labels, metadata */
--text-sm: 11px;    /* Secondary info */
--text-base: 13px;  /* Body text */
--text-md: 14px;    /* Buttons, inputs */
--text-lg: 17px;    /* Section titles */
--text-xl: 24px;    /* Screen titles */
--text-2xl: 28px;   /* Hero numbers */
--text-3xl: 36px;   /* Large stats */

/* Font Weights */
--font-light: 300;
--font-regular: 400;
--font-medium: 500;
--font-semibold: 600;
--font-bold: 700;
```

### Color System

```css
:root {
  /* ===== SHARED ACCENTS ===== */
  --accent-blue: #0A84FF;
  --accent-green: #30D158;
  --accent-orange: #FF9F0A;
  --accent-red: #FF453A;
  --accent-purple: #BF5AF2;
  --accent-teal: #64D2FF;
  --accent-pink: #FF375F;
  --accent-yellow: #FFD60A;

  /* ===== GRADIENTS ===== */
  --gradient-hero: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  --gradient-success: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
  --gradient-warning: linear-gradient(135deg, #F2994A 0%, #F2C94C 100%);
  --gradient-danger: linear-gradient(135deg, #eb3349 0%, #f45c43 100%);
  --gradient-cool: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%);
  --gradient-ocean: linear-gradient(135deg, #2E3192 0%, #1BFFFF 100%);
  --gradient-sunset: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
  --gradient-forest: linear-gradient(135deg, #134E5E 0%, #71B280 100%);

  /* ===== BORDER RADIUS ===== */
  --radius-sm: 12px;
  --radius-md: 20px;
  --radius-lg: 28px;
  --radius-xl: 40px;
  --radius-full: 9999px;

  /* ===== TRANSITIONS ===== */
  --transition-fast: 0.15s ease;
  --transition-base: 0.3s ease;
  --transition-slow: 0.5s cubic-bezier(0.16, 1, 0.3, 1);
  --transition-theme: 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

/* ===== DARK THEME ===== */
[data-theme="dark"] {
  --bg-primary: #000000;
  --bg-secondary: #0a0a0a;
  --bg-tertiary: #141414;
  --bg-card: rgba(255, 255, 255, 0.05);
  --bg-card-hover: rgba(255, 255, 255, 0.08);
  --bg-glass: rgba(255, 255, 255, 0.03);
  --bg-input: rgba(255, 255, 255, 0.05);

  --text-primary: #ffffff;
  --text-secondary: rgba(255, 255, 255, 0.7);
  --text-tertiary: rgba(255, 255, 255, 0.4);

  --border-subtle: rgba(255, 255, 255, 0.08);
  --border-medium: rgba(255, 255, 255, 0.12);

  --shadow-card: 0 8px 32px rgba(0, 0, 0, 0.4);
  --shadow-elevated: 0 20px 60px rgba(0, 0, 0, 0.5);
  --shadow-glow: 0 0 40px rgba(10, 132, 255, 0.3);

  --device-bg: linear-gradient(145deg, #1a1a1a 0%, #0d0d0d 100%);
  --device-border: rgba(255, 255, 255, 0.1);
  --nav-bg: rgba(30, 30, 30, 0.8);
  --orb-opacity: 0.4;
}

/* ===== LIGHT THEME ===== */
[data-theme="light"] {
  --bg-primary: #f5f5f7;
  --bg-secondary: #ffffff;
  --bg-tertiary: #f0f0f2;
  --bg-card: rgba(0, 0, 0, 0.03);
  --bg-card-hover: rgba(0, 0, 0, 0.05);
  --bg-glass: rgba(255, 255, 255, 0.7);
  --bg-input: rgba(0, 0, 0, 0.04);

  --text-primary: #1d1d1f;
  --text-secondary: rgba(0, 0, 0, 0.6);
  --text-tertiary: rgba(0, 0, 0, 0.4);

  --border-subtle: rgba(0, 0, 0, 0.06);
  --border-medium: rgba(0, 0, 0, 0.1);

  --shadow-card: 0 4px 20px rgba(0, 0, 0, 0.08);
  --shadow-elevated: 0 12px 40px rgba(0, 0, 0, 0.12);
  --shadow-glow: 0 0 40px rgba(10, 132, 255, 0.15);

  --device-bg: linear-gradient(145deg, #ffffff 0%, #f8f8f8 100%);
  --device-border: rgba(0, 0, 0, 0.1);
  --nav-bg: rgba(255, 255, 255, 0.85);
  --orb-opacity: 0.15;
}
```

---

## Component Library

### 1. Device Frame (iPhone 15 Pro Style)

```html
<div class="device">
  <div class="dynamic-island"></div>
  <div class="screen">
    <div class="screen-content">
      <!-- Content here -->
    </div>
    <div class="bottom-nav">
      <!-- Navigation -->
    </div>
    <div class="home-indicator"></div>
  </div>
  <div class="screen-label">
    <span class="screen-number">01</span>
    <span class="screen-name">Screen Name</span>
  </div>
</div>
```

```css
.device {
  width: 280px;
  height: 580px;
  background: var(--device-bg);
  border-radius: 48px;
  padding: 12px;
  position: relative;
  box-shadow: 0 0 0 1px var(--device-border), var(--shadow-elevated);
  transition: all 0.5s cubic-bezier(0.16, 1, 0.3, 1);
}

.device:hover {
  transform: translateY(-10px) scale(1.02);
  box-shadow: 0 0 0 1px var(--device-border), 0 30px 80px rgba(0,0,0,0.3), var(--shadow-glow);
}

.dynamic-island {
  position: absolute;
  top: 16px;
  left: 50%;
  transform: translateX(-50%);
  width: 90px;
  height: 26px;
  background: #000;
  border-radius: 20px;
  z-index: 10;
  transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
}

.device:hover .dynamic-island {
  width: 120px;
  background: var(--gradient-hero);
}

.screen {
  width: 100%;
  height: 100%;
  background: var(--bg-secondary);
  border-radius: 40px;
  overflow: hidden;
  position: relative;
}

.home-indicator {
  position: absolute;
  bottom: 8px;
  left: 50%;
  transform: translateX(-50%);
  width: 120px;
  height: 4px;
  background: var(--text-tertiary);
  border-radius: 2px;
  opacity: 0.5;
}
```

### 2. Glass Card

```html
<div class="glass-card">
  <!-- Content -->
</div>

<div class="glass-card glow-blue">
  <!-- With blue glow -->
</div>
```

```css
.glass-card {
  background: var(--bg-card);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-subtle);
  padding: 16px;
  margin-bottom: 12px;
  transition: all var(--transition-base);
}

.glass-card:hover {
  background: var(--bg-card-hover);
  border-color: var(--border-medium);
  transform: translateY(-2px);
}

.glass-card.glow-blue {
  border-color: rgba(10, 132, 255, 0.4);
  box-shadow: 0 0 20px rgba(10, 132, 255, 0.1);
}

.glass-card.glow-green {
  border-color: rgba(48, 209, 88, 0.4);
  box-shadow: 0 0 20px rgba(48, 209, 88, 0.1);
}

.glass-card.glow-orange {
  border-color: rgba(255, 159, 10, 0.4);
  box-shadow: 0 0 20px rgba(255, 159, 10, 0.1);
}

.glass-card.glow-red {
  border-color: rgba(255, 69, 58, 0.4);
  box-shadow: 0 0 20px rgba(255, 69, 58, 0.1);
}
```

### 3. Status Pills

```html
<span class="status-pill urgent"><span class="status-dot"></span>Urgent</span>
<span class="status-pill progress">In Progress</span>
<span class="status-pill success">Complete</span>
<span class="status-pill info">Info</span>
```

```css
.status-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 10px;
  border-radius: 20px;
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.status-pill.urgent {
  background: rgba(255, 69, 58, 0.15);
  color: var(--accent-red);
}

.status-pill.progress {
  background: rgba(255, 159, 10, 0.15);
  color: var(--accent-orange);
}

.status-pill.success {
  background: rgba(48, 209, 88, 0.15);
  color: var(--accent-green);
}

.status-pill.info {
  background: rgba(10, 132, 255, 0.15);
  color: var(--accent-blue);
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
  animation: pulse-dot 2s infinite;
}

@keyframes pulse-dot {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}
```

### 4. Buttons

```html
<button class="btn-primary">Primary Action</button>
<button class="btn-secondary">Secondary</button>
```

```css
.btn-primary {
  width: 100%;
  padding: 15px 24px;
  background: var(--gradient-hero);
  border: none;
  border-radius: var(--radius-md);
  color: white;
  font-family: inherit;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all var(--transition-base);
}

.btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4);
}

.btn-secondary {
  width: 100%;
  padding: 14px 24px;
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  color: var(--text-primary);
  font-family: inherit;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--transition-base);
}

.btn-secondary:hover {
  background: var(--bg-card-hover);
  border-color: var(--border-medium);
}
```

### 5. Input Fields

```html
<input type="text" class="input-field" placeholder="Enter text...">
```

```css
.input-field {
  width: 100%;
  padding: 15px 18px;
  background: var(--bg-input);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  color: var(--text-primary);
  font-family: inherit;
  font-size: 14px;
  transition: all var(--transition-base);
  margin-bottom: 12px;
}

.input-field::placeholder {
  color: var(--text-tertiary);
}

.input-field:focus {
  outline: none;
  border-color: var(--accent-blue);
  box-shadow: 0 0 0 4px rgba(10, 132, 255, 0.1);
}
```

### 6. Voice Button (Voice-First UX)

```html
<button class="voice-btn" id="voiceBtn">🎤</button>
```

```css
.voice-btn {
  width: 72px;
  height: 72px;
  border-radius: 50%;
  background: var(--gradient-hero);
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  cursor: pointer;
  margin: 20px auto;
  position: relative;
  box-shadow: 0 8px 30px rgba(102, 126, 234, 0.4);
  transition: all var(--transition-base);
}

.voice-btn::before {
  content: '';
  position: absolute;
  inset: -4px;
  border-radius: 50%;
  background: var(--gradient-hero);
  opacity: 0.3;
  z-index: -1;
  animation: voice-pulse 2s infinite;
}

@keyframes voice-pulse {
  0%, 100% { transform: scale(1); opacity: 0.3; }
  50% { transform: scale(1.15); opacity: 0; }
}

.voice-btn:hover {
  transform: scale(1.1);
}

.voice-btn.recording {
  background: var(--gradient-danger);
}
```

### 7. Bottom Navigation

```html
<div class="bottom-nav">
  <div class="nav-item active"><span class="nav-icon">🏠</span><span class="nav-label">Home</span></div>
  <div class="nav-item"><span class="nav-icon">➕</span><span class="nav-label">Add</span></div>
  <div class="nav-item"><span class="nav-icon">💬</span><span class="nav-label">Chat</span></div>
  <div class="nav-item"><span class="nav-icon">👤</span><span class="nav-label">Profile</span></div>
</div>
```

```css
.bottom-nav {
  position: absolute;
  bottom: 24px;
  left: 16px;
  right: 16px;
  background: var(--nav-bg);
  backdrop-filter: blur(20px);
  border-radius: var(--radius-lg);
  padding: 10px 6px;
  display: flex;
  justify-content: space-around;
  border: 1px solid var(--border-subtle);
}

.nav-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 3px;
  cursor: pointer;
  padding: 6px 12px;
  border-radius: var(--radius-sm);
  transition: all var(--transition-base);
}

.nav-item:hover {
  background: var(--bg-card);
}

.nav-item.active {
  background: rgba(10, 132, 255, 0.15);
}

.nav-item.active .nav-icon,
.nav-item.active .nav-label {
  color: var(--accent-blue);
}

.nav-icon {
  font-size: 18px;
}

.nav-label {
  font-size: 9px;
  color: var(--text-tertiary);
}
```

### 8. Stats Grid

```html
<div class="stat-grid">
  <div class="stat-card">
    <div class="stat-number red">5</div>
    <div class="stat-label">Open</div>
  </div>
  <div class="stat-card">
    <div class="stat-number green">12</div>
    <div class="stat-label">Done</div>
  </div>
</div>
```

```css
.stat-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}

.stat-card {
  background: var(--bg-card);
  border-radius: var(--radius-md);
  padding: 16px;
  text-align: center;
  border: 1px solid var(--border-subtle);
  transition: all var(--transition-base);
}

.stat-card:hover {
  transform: scale(1.03);
}

.stat-number {
  font-size: 28px;
  font-weight: 700;
  background: var(--gradient-hero);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.stat-number.red {
  background: var(--gradient-danger);
  -webkit-background-clip: text;
  background-clip: text;
}

.stat-number.green {
  background: var(--gradient-success);
  -webkit-background-clip: text;
  background-clip: text;
}

.stat-number.orange {
  background: var(--gradient-warning);
  -webkit-background-clip: text;
  background-clip: text;
}

.stat-label {
  font-size: 10px;
  color: var(--text-tertiary);
  text-transform: uppercase;
  letter-spacing: 1px;
  margin-top: 4px;
}
```

### 9. Timeline

```html
<div class="timeline">
  <div class="timeline-item complete">
    <div class="timeline-title">Step Complete</div>
    <div class="timeline-meta">Jan 20, 2:00 PM</div>
  </div>
  <div class="timeline-item active">
    <div class="timeline-title">Current Step</div>
    <div class="timeline-meta">In progress</div>
  </div>
</div>
```

```css
.timeline {
  position: relative;
  padding-left: 24px;
}

.timeline::before {
  content: '';
  position: absolute;
  left: 7px;
  top: 8px;
  bottom: 8px;
  width: 2px;
  background: linear-gradient(180deg, var(--accent-blue), var(--accent-purple), var(--accent-green));
  border-radius: 1px;
}

.timeline-item {
  position: relative;
  margin-bottom: 14px;
  padding-left: 8px;
}

.timeline-item::before {
  content: '';
  position: absolute;
  left: -20px;
  top: 5px;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: var(--bg-secondary);
  border: 2px solid var(--accent-blue);
}

.timeline-item.complete::before {
  background: var(--accent-green);
  border-color: var(--accent-green);
}

.timeline-item.active::before {
  background: var(--accent-blue);
  border-color: var(--accent-blue);
  box-shadow: 0 0 10px var(--accent-blue);
}

.timeline-title {
  font-size: 12px;
  font-weight: 600;
}

.timeline-meta {
  font-size: 10px;
  color: var(--text-tertiary);
}
```

### 10. Feature Badge (AI Indicator)

```html
<span class="feature-badge">🤖 AI POWERED</span>
```

```css
.feature-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  background: rgba(191, 90, 242, 0.15);
  border-radius: 12px;
  font-size: 10px;
  color: var(--accent-purple);
  font-weight: 600;
}
```

### 11. Toggle Switch

```html
<div class="toggle-row">
  <span class="toggle-label">Setting Name</span>
  <div class="toggle active"></div>
</div>
```

```css
.toggle-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 0;
  border-bottom: 1px solid var(--border-subtle);
}

.toggle-label {
  font-size: 13px;
  color: var(--text-primary);
}

.toggle {
  width: 48px;
  height: 28px;
  background: var(--bg-tertiary);
  border-radius: 14px;
  position: relative;
  cursor: pointer;
  transition: all var(--transition-base);
}

.toggle.active {
  background: var(--accent-green);
}

.toggle::after {
  content: '';
  position: absolute;
  width: 22px;
  height: 22px;
  background: white;
  border-radius: 50%;
  top: 3px;
  left: 3px;
  transition: all var(--transition-base);
  box-shadow: 0 2px 8px rgba(0,0,0,0.2);
}

.toggle.active::after {
  left: 23px;
}
```

### 12. ETA/Progress Card

```html
<div class="eta-card">
  <div class="eta-label">Arriving in</div>
  <div class="eta-time">~12 min</div>
  <div class="eta-progress"><div class="eta-bar"></div></div>
</div>
```

```css
.eta-card {
  background: linear-gradient(135deg, rgba(10, 132, 255, 0.15) 0%, rgba(191, 90, 242, 0.15) 100%);
  border-radius: var(--radius-md);
  padding: 20px;
  margin-bottom: 16px;
  border: 1px solid rgba(10, 132, 255, 0.3);
  text-align: center;
}

.eta-time {
  font-size: 36px;
  font-weight: 700;
  background: linear-gradient(135deg, var(--accent-blue), var(--accent-purple));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.eta-label {
  font-size: 12px;
  color: var(--text-secondary);
}

.eta-progress {
  height: 4px;
  background: var(--bg-card);
  border-radius: 2px;
  margin-top: 16px;
  overflow: hidden;
}

.eta-bar {
  height: 100%;
  width: 65%;
  background: linear-gradient(90deg, var(--accent-blue), var(--accent-purple));
  border-radius: 2px;
}
```

---

## Ambient Background System

```html
<div class="ambient-bg">
  <div class="ambient-orb orb-1"></div>
  <div class="ambient-orb orb-2"></div>
  <div class="ambient-orb orb-3"></div>
</div>
```

```css
.ambient-bg {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: -1;
  overflow: hidden;
}

.ambient-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(100px);
  opacity: var(--orb-opacity);
  animation: float 20s infinite ease-in-out;
}

.orb-1 {
  width: 600px;
  height: 600px;
  background: var(--accent-purple);
  top: -200px;
  right: -200px;
}

.orb-2 {
  width: 500px;
  height: 500px;
  background: var(--accent-blue);
  bottom: -150px;
  left: -150px;
  animation-delay: -7s;
}

.orb-3 {
  width: 400px;
  height: 400px;
  background: var(--accent-teal);
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  animation-delay: -14s;
}

@keyframes float {
  0%, 100% { transform: translate(0, 0) scale(1); }
  33% { transform: translate(30px, -30px) scale(1.05); }
  66% { transform: translate(-20px, 20px) scale(0.95); }
}
```

---

## Theme Toggle System

```html
<div class="theme-toggle-container">
  <span class="theme-label">Theme</span>
  <div class="theme-toggle" id="themeToggle"></div>
</div>
```

```css
.theme-toggle-container {
  position: fixed;
  top: 20px;
  right: 20px;
  z-index: 1000;
  display: flex;
  align-items: center;
  gap: 12px;
  background: var(--bg-card);
  backdrop-filter: blur(20px);
  padding: 8px 16px;
  border-radius: 50px;
  border: 1px solid var(--border-subtle);
}

.theme-toggle {
  width: 56px;
  height: 28px;
  background: var(--bg-tertiary);
  border-radius: 14px;
  position: relative;
  cursor: pointer;
  border: 1px solid var(--border-subtle);
}

.theme-toggle::before {
  content: '🌙';
  position: absolute;
  left: 4px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 12px;
}

.theme-toggle::after {
  content: '';
  position: absolute;
  width: 22px;
  height: 22px;
  background: var(--gradient-hero);
  border-radius: 50%;
  top: 2px;
  left: 2px;
  transition: all var(--transition-theme);
}

[data-theme="light"] .theme-toggle::before {
  content: '☀️';
  left: auto;
  right: 4px;
}

[data-theme="light"] .theme-toggle::after {
  left: 30px;
  background: var(--gradient-warning);
}
```

```javascript
// Theme Toggle Logic
const themeToggle = document.getElementById('themeToggle');
const html = document.documentElement;

const savedTheme = localStorage.getItem('theme') || 'dark';
html.setAttribute('data-theme', savedTheme);

themeToggle.addEventListener('click', () => {
  const current = html.getAttribute('data-theme');
  const next = current === 'dark' ? 'light' : 'dark';
  html.setAttribute('data-theme', next);
  localStorage.setItem('theme', next);
});
```

---

## Color Presets

Alternative color palettes that complement the default Aurora accent system (Blue #0A84FF, Green #30D158, Purple #BF5AF2). Use these presets to give each project a distinct personality while maintaining Aurora's glassmorphism and ambient orb aesthetics.

### How to Apply a Preset

Override the default accent variables inside `:root` and adjust the theme-specific tokens. Each preset provides both dark and light theme values.

```css
/* Example: Apply the Ocean preset */
:root {
  --preset-primary: var(--ocean-primary);
  --preset-secondary: var(--ocean-secondary);
  --preset-accent: var(--ocean-accent);
  --preset-surface: var(--ocean-surface);
}
```

### Preset 1: Ocean — Cool, professional, trustworthy

```css
:root {
  --ocean-primary: #3B82F6;
  --ocean-secondary: #06B6D4;
  --ocean-accent: #0EA5E9;
  --ocean-surface-dark: #0c1929;
  --ocean-surface-light: #f0f7ff;
  --ocean-text-dark: #e2eeff;
  --ocean-text-light: #0f2b4a;
}

/* Ocean Dark Theme */
[data-theme="dark"][data-preset="ocean"] {
  --bg-primary: #000a14;
  --bg-secondary: #0c1929;
  --bg-tertiary: #132438;
  --bg-card: rgba(59, 130, 246, 0.06);
  --bg-card-hover: rgba(59, 130, 246, 0.10);
  --text-primary: #e2eeff;
  --text-secondary: rgba(226, 238, 255, 0.7);
  --text-tertiary: rgba(226, 238, 255, 0.4);
  --accent-blue: #3B82F6;
  --accent-green: #06B6D4;
  --accent-purple: #0EA5E9;
  --shadow-glow: 0 0 40px rgba(59, 130, 246, 0.3);
  --gradient-hero: linear-gradient(135deg, #3B82F6 0%, #06B6D4 100%);
}

/* Ocean Light Theme */
[data-theme="light"][data-preset="ocean"] {
  --bg-primary: #f0f7ff;
  --bg-secondary: #ffffff;
  --bg-tertiary: #e8f1fd;
  --bg-card: rgba(59, 130, 246, 0.05);
  --bg-card-hover: rgba(59, 130, 246, 0.08);
  --text-primary: #0f2b4a;
  --text-secondary: rgba(15, 43, 74, 0.65);
  --text-tertiary: rgba(15, 43, 74, 0.4);
  --accent-blue: #2563EB;
  --accent-green: #0891B2;
  --accent-purple: #0284C7;
  --shadow-glow: 0 0 40px rgba(59, 130, 246, 0.15);
  --gradient-hero: linear-gradient(135deg, #2563EB 0%, #0891B2 100%);
}
```

### Preset 2: Sunset — Warm, energetic, creative

```css
:root {
  --sunset-primary: #F97316;
  --sunset-secondary: #F43F5E;
  --sunset-accent: #EAB308;
  --sunset-surface-dark: #1a0e08;
  --sunset-surface-light: #fff8f0;
  --sunset-text-dark: #ffe8d6;
  --sunset-text-light: #4a1e08;
}

/* Sunset Dark Theme */
[data-theme="dark"][data-preset="sunset"] {
  --bg-primary: #0a0604;
  --bg-secondary: #1a0e08;
  --bg-tertiary: #2a1810;
  --bg-card: rgba(249, 115, 22, 0.06);
  --bg-card-hover: rgba(249, 115, 22, 0.10);
  --text-primary: #ffe8d6;
  --text-secondary: rgba(255, 232, 214, 0.7);
  --text-tertiary: rgba(255, 232, 214, 0.4);
  --accent-blue: #F97316;
  --accent-green: #EAB308;
  --accent-purple: #F43F5E;
  --shadow-glow: 0 0 40px rgba(249, 115, 22, 0.3);
  --gradient-hero: linear-gradient(135deg, #F97316 0%, #F43F5E 100%);
}

/* Sunset Light Theme */
[data-theme="light"][data-preset="sunset"] {
  --bg-primary: #fff8f0;
  --bg-secondary: #ffffff;
  --bg-tertiary: #fff0e0;
  --bg-card: rgba(249, 115, 22, 0.05);
  --bg-card-hover: rgba(249, 115, 22, 0.08);
  --text-primary: #4a1e08;
  --text-secondary: rgba(74, 30, 8, 0.65);
  --text-tertiary: rgba(74, 30, 8, 0.4);
  --accent-blue: #EA580C;
  --accent-green: #CA8A04;
  --accent-purple: #E11D48;
  --shadow-glow: 0 0 40px rgba(249, 115, 22, 0.15);
  --gradient-hero: linear-gradient(135deg, #EA580C 0%, #E11D48 100%);
}
```

### Preset 3: Forest — Natural, calm, growth-oriented

```css
:root {
  --forest-primary: #10B981;
  --forest-secondary: #059669;
  --forest-accent: #84CC16;
  --forest-surface-dark: #071a12;
  --forest-surface-light: #f0fdf4;
  --forest-text-dark: #d1fae5;
  --forest-text-light: #14532d;
}

/* Forest Dark Theme */
[data-theme="dark"][data-preset="forest"] {
  --bg-primary: #020a06;
  --bg-secondary: #071a12;
  --bg-tertiary: #0c261a;
  --bg-card: rgba(16, 185, 129, 0.06);
  --bg-card-hover: rgba(16, 185, 129, 0.10);
  --text-primary: #d1fae5;
  --text-secondary: rgba(209, 250, 229, 0.7);
  --text-tertiary: rgba(209, 250, 229, 0.4);
  --accent-blue: #10B981;
  --accent-green: #84CC16;
  --accent-purple: #059669;
  --shadow-glow: 0 0 40px rgba(16, 185, 129, 0.3);
  --gradient-hero: linear-gradient(135deg, #10B981 0%, #059669 100%);
}

/* Forest Light Theme */
[data-theme="light"][data-preset="forest"] {
  --bg-primary: #f0fdf4;
  --bg-secondary: #ffffff;
  --bg-tertiary: #dcfce7;
  --bg-card: rgba(16, 185, 129, 0.05);
  --bg-card-hover: rgba(16, 185, 129, 0.08);
  --text-primary: #14532d;
  --text-secondary: rgba(20, 83, 45, 0.65);
  --text-tertiary: rgba(20, 83, 45, 0.4);
  --accent-blue: #059669;
  --accent-green: #65A30D;
  --accent-purple: #047857;
  --shadow-glow: 0 0 40px rgba(16, 185, 129, 0.15);
  --gradient-hero: linear-gradient(135deg, #059669 0%, #047857 100%);
}
```

### Preset 4: Midnight — Premium, luxurious, sophisticated

```css
:root {
  --midnight-primary: #8B5CF6;
  --midnight-secondary: #6366F1;
  --midnight-accent: #EC4899;
  --midnight-surface-dark: #0f0a1a;
  --midnight-surface-light: #f5f0ff;
  --midnight-text-dark: #e8deff;
  --midnight-text-light: #2e1065;
}

/* Midnight Dark Theme */
[data-theme="dark"][data-preset="midnight"] {
  --bg-primary: #050210;
  --bg-secondary: #0f0a1a;
  --bg-tertiary: #1a1228;
  --bg-card: rgba(139, 92, 246, 0.06);
  --bg-card-hover: rgba(139, 92, 246, 0.10);
  --text-primary: #e8deff;
  --text-secondary: rgba(232, 222, 255, 0.7);
  --text-tertiary: rgba(232, 222, 255, 0.4);
  --accent-blue: #8B5CF6;
  --accent-green: #EC4899;
  --accent-purple: #6366F1;
  --shadow-glow: 0 0 40px rgba(139, 92, 246, 0.3);
  --gradient-hero: linear-gradient(135deg, #8B5CF6 0%, #6366F1 100%);
}

/* Midnight Light Theme */
[data-theme="light"][data-preset="midnight"] {
  --bg-primary: #f5f0ff;
  --bg-secondary: #ffffff;
  --bg-tertiary: #ede5ff;
  --bg-card: rgba(139, 92, 246, 0.05);
  --bg-card-hover: rgba(139, 92, 246, 0.08);
  --text-primary: #2e1065;
  --text-secondary: rgba(46, 16, 101, 0.65);
  --text-tertiary: rgba(46, 16, 101, 0.4);
  --accent-blue: #7C3AED;
  --accent-green: #DB2777;
  --accent-purple: #4F46E5;
  --shadow-glow: 0 0 40px rgba(139, 92, 246, 0.15);
  --gradient-hero: linear-gradient(135deg, #7C3AED 0%, #4F46E5 100%);
}
```

### Preset 5: Coral — Friendly, inviting, social

```css
:root {
  --coral-primary: #FB7185;
  --coral-secondary: #F472B6;
  --coral-accent: #FBBF24;
  --coral-surface-dark: #1a0a10;
  --coral-surface-light: #fff5f7;
  --coral-text-dark: #ffe0e8;
  --coral-text-light: #4a0e1e;
}

/* Coral Dark Theme */
[data-theme="dark"][data-preset="coral"] {
  --bg-primary: #0a0408;
  --bg-secondary: #1a0a10;
  --bg-tertiary: #2a1018;
  --bg-card: rgba(251, 113, 133, 0.06);
  --bg-card-hover: rgba(251, 113, 133, 0.10);
  --text-primary: #ffe0e8;
  --text-secondary: rgba(255, 224, 232, 0.7);
  --text-tertiary: rgba(255, 224, 232, 0.4);
  --accent-blue: #FB7185;
  --accent-green: #FBBF24;
  --accent-purple: #F472B6;
  --shadow-glow: 0 0 40px rgba(251, 113, 133, 0.3);
  --gradient-hero: linear-gradient(135deg, #FB7185 0%, #F472B6 100%);
}

/* Coral Light Theme */
[data-theme="light"][data-preset="coral"] {
  --bg-primary: #fff5f7;
  --bg-secondary: #ffffff;
  --bg-tertiary: #ffe4ea;
  --bg-card: rgba(251, 113, 133, 0.05);
  --bg-card-hover: rgba(251, 113, 133, 0.08);
  --text-primary: #4a0e1e;
  --text-secondary: rgba(74, 14, 30, 0.65);
  --text-tertiary: rgba(74, 14, 30, 0.4);
  --accent-blue: #E11D48;
  --accent-green: #D97706;
  --accent-purple: #DB2777;
  --shadow-glow: 0 0 40px rgba(251, 113, 133, 0.15);
  --gradient-hero: linear-gradient(135deg, #E11D48 0%, #DB2777 100%);
}
```

### Preset Quick-Reference Table

| Preset | Primary | Secondary | Accent | Mood |
|--------|---------|-----------|--------|------|
| **Ocean** | `#3B82F6` | `#06B6D4` | `#0EA5E9` | Cool, professional, trustworthy |
| **Sunset** | `#F97316` | `#F43F5E` | `#EAB308` | Warm, energetic, creative |
| **Forest** | `#10B981` | `#059669` | `#84CC16` | Natural, calm, growth-oriented |
| **Midnight** | `#8B5CF6` | `#6366F1` | `#EC4899` | Premium, luxurious, sophisticated |
| **Coral** | `#FB7185` | `#F472B6` | `#FBBF24` | Friendly, inviting, social |

### Preset Selection JavaScript

```javascript
// Apply a color preset programmatically
function applyPreset(presetName) {
  document.documentElement.setAttribute('data-preset', presetName);
  localStorage.setItem('color-preset', presetName);
}

// Restore saved preset on load
const savedPreset = localStorage.getItem('color-preset');
if (savedPreset) {
  document.documentElement.setAttribute('data-preset', savedPreset);
}
```

---

## Screen-Type Component Library

Recommended component patterns for common screen types. Each entry lists the key UI elements and provides HTML/CSS snippets following Aurora 2026 conventions.

### Dashboard / Home Screen

Key components: stat cards, progress rings, quick-action grid, recent activity list.

```html
<!-- Stat Cards Row -->
<div class="stat-grid">
  <div class="glass-card stat-card">
    <div class="stat-number" style="background:var(--gradient-hero);-webkit-background-clip:text;-webkit-text-fill-color:transparent;">247</div>
    <div class="stat-label">Total Tasks</div>
  </div>
  <div class="glass-card stat-card">
    <div class="stat-number" style="background:var(--gradient-success);-webkit-background-clip:text;-webkit-text-fill-color:transparent;">89%</div>
    <div class="stat-label">Complete</div>
  </div>
</div>

<!-- Progress Ring -->
<div class="progress-ring-container">
  <svg class="progress-ring" width="80" height="80">
    <circle class="progress-ring-bg" cx="40" cy="40" r="34" fill="none" stroke="var(--bg-card)" stroke-width="6"/>
    <circle class="progress-ring-fill" cx="40" cy="40" r="34" fill="none" stroke="var(--accent-blue)" stroke-width="6"
      stroke-dasharray="213.6" stroke-dashoffset="64" stroke-linecap="round" transform="rotate(-90 40 40)"/>
  </svg>
  <span class="progress-ring-label">70%</span>
</div>

<!-- Quick-Action Grid -->
<div class="quick-actions">
  <button class="quick-action-btn glass-card"><span>📝</span><span class="quick-action-label">New Task</span></button>
  <button class="quick-action-btn glass-card"><span>📊</span><span class="quick-action-label">Reports</span></button>
  <button class="quick-action-btn glass-card"><span>👥</span><span class="quick-action-label">Team</span></button>
  <button class="quick-action-btn glass-card"><span>⚙️</span><span class="quick-action-label">Settings</span></button>
</div>
```

```css
.progress-ring-container {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.progress-ring-label {
  position: absolute;
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary);
}
.quick-actions {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
  margin-bottom: 16px;
}
.quick-action-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 14px 8px;
  border: none;
  cursor: pointer;
  font-family: inherit;
  background: var(--bg-card);
  border-radius: var(--radius-md);
  transition: all var(--transition-base);
}
.quick-action-btn:hover { transform: translateY(-2px); }
.quick-action-label {
  font-size: 10px;
  color: var(--text-secondary);
}
```

### Settings / Profile Screen

Key components: toggle groups, section headers with descriptions, avatar upload area, info rows.

```html
<!-- Profile Header -->
<div class="profile-header">
  <div class="avatar-upload">
    <div class="avatar-circle">JD</div>
    <div class="avatar-edit-badge">📷</div>
  </div>
  <div class="profile-name">Jane Doe</div>
  <div class="profile-email" style="font-size:11px;color:var(--text-tertiary);">jane.doe@email.com</div>
</div>

<!-- Settings Section -->
<div class="settings-section">
  <div class="settings-section-header">
    <span class="settings-section-title">Notifications</span>
    <span class="settings-section-desc">Control how you receive alerts</span>
  </div>
  <div class="toggle-row"><span class="toggle-label">Push Notifications</span><div class="toggle active"></div></div>
  <div class="toggle-row"><span class="toggle-label">Email Digest</span><div class="toggle"></div></div>
  <div class="toggle-row"><span class="toggle-label">Sound Effects</span><div class="toggle active"></div></div>
</div>

<!-- Info Row -->
<div class="info-row">
  <span class="info-row-label">App Version</span>
  <span class="info-row-value">2.4.1</span>
  <span class="info-row-chevron">›</span>
</div>
```

```css
.profile-header {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 20px 0;
  gap: 6px;
}
.avatar-circle {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: var(--gradient-hero);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  font-weight: 700;
  color: #fff;
}
.avatar-upload { position: relative; }
.avatar-edit-badge {
  position: absolute;
  bottom: -2px;
  right: -2px;
  width: 24px;
  height: 24px;
  background: var(--bg-secondary);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  border: 2px solid var(--border-subtle);
}
.profile-name { font-size: 17px; font-weight: 600; color: var(--text-primary); }
.settings-section { margin-bottom: 20px; }
.settings-section-header { padding: 12px 0 6px; }
.settings-section-title { font-size: 13px; font-weight: 600; color: var(--text-primary); display: block; }
.settings-section-desc { font-size: 10px; color: var(--text-tertiary); }
.info-row {
  display: flex;
  align-items: center;
  padding: 14px 0;
  border-bottom: 1px solid var(--border-subtle);
}
.info-row-label { font-size: 13px; color: var(--text-primary); flex: 1; }
.info-row-value { font-size: 12px; color: var(--text-tertiary); margin-right: 8px; }
.info-row-chevron { color: var(--text-tertiary); font-size: 16px; }
```

### Chat / Messaging Screen

Key components: message bubbles (sent/received), input bar with attachments, typing indicator, read receipts.

```html
<!-- Message Thread -->
<div class="chat-messages">
  <div class="message received">
    <div class="message-bubble">Hey, how's the project going?</div>
    <span class="message-time">2:30 PM</span>
  </div>
  <div class="message sent">
    <div class="message-bubble">Almost done! Finishing the last screen now.</div>
    <span class="message-meta"><span class="read-receipt">✓✓</span> 2:32 PM</span>
  </div>
  <div class="typing-indicator">
    <span class="typing-dot"></span><span class="typing-dot"></span><span class="typing-dot"></span>
  </div>
</div>

<!-- Chat Input Bar -->
<div class="chat-input-bar">
  <button class="chat-attach-btn">+</button>
  <input type="text" class="chat-input" placeholder="Type a message...">
  <button class="chat-send-btn">↑</button>
</div>
```

```css
.chat-messages { padding: 16px 12px; display: flex; flex-direction: column; gap: 10px; }
.message { display: flex; flex-direction: column; max-width: 80%; }
.message.sent { align-self: flex-end; align-items: flex-end; }
.message.received { align-self: flex-start; align-items: flex-start; }
.message-bubble {
  padding: 10px 14px;
  border-radius: 18px;
  font-size: 13px;
  line-height: 1.4;
}
.message.sent .message-bubble {
  background: var(--gradient-hero);
  color: #fff;
  border-bottom-right-radius: 4px;
}
.message.received .message-bubble {
  background: var(--bg-card);
  color: var(--text-primary);
  border: 1px solid var(--border-subtle);
  border-bottom-left-radius: 4px;
}
.message-time, .message-meta { font-size: 9px; color: var(--text-tertiary); margin-top: 3px; }
.read-receipt { color: var(--accent-blue); margin-right: 3px; }
.typing-indicator { display: flex; gap: 4px; padding: 8px 14px; align-self: flex-start; }
.typing-dot {
  width: 6px; height: 6px; border-radius: 50%;
  background: var(--text-tertiary);
  animation: typing-bounce 1.4s infinite;
}
.typing-dot:nth-child(2) { animation-delay: 0.2s; }
.typing-dot:nth-child(3) { animation-delay: 0.4s; }
@keyframes typing-bounce {
  0%, 60%, 100% { transform: translateY(0); }
  30% { transform: translateY(-6px); }
}
.chat-input-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  background: var(--nav-bg);
  backdrop-filter: blur(20px);
  border-top: 1px solid var(--border-subtle);
}
.chat-input {
  flex: 1;
  padding: 10px 14px;
  background: var(--bg-input);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-full);
  color: var(--text-primary);
  font-family: inherit;
  font-size: 13px;
}
.chat-attach-btn, .chat-send-btn {
  width: 36px; height: 36px; border-radius: 50%; border: none;
  display: flex; align-items: center; justify-content: center;
  font-size: 18px; cursor: pointer; transition: all var(--transition-base);
}
.chat-attach-btn { background: var(--bg-card); color: var(--text-secondary); }
.chat-send-btn { background: var(--gradient-hero); color: #fff; }
```

### List / Feed Screen

Key components: card items with thumbnails, pull-to-refresh indicator, filter chips, empty state.

```html
<!-- Filter Chips -->
<div class="filter-chips">
  <button class="chip active">All</button>
  <button class="chip">Popular</button>
  <button class="chip">Recent</button>
  <button class="chip">Saved</button>
</div>

<!-- Feed Card -->
<div class="feed-card glass-card">
  <div class="feed-thumb" style="background:var(--gradient-cool);"></div>
  <div class="feed-content">
    <div class="feed-title">Morning Run - 5.2km</div>
    <div class="feed-subtitle">Central Park Loop</div>
    <div class="feed-meta">
      <span class="status-pill success">Complete</span>
      <span class="feed-time">2h ago</span>
    </div>
  </div>
</div>

<!-- Empty State -->
<div class="empty-state">
  <div class="empty-icon">📭</div>
  <div class="empty-title">Nothing here yet</div>
  <div class="empty-desc">Your items will appear once you get started.</div>
  <button class="btn-primary" style="width:auto;padding:12px 32px;">Get Started</button>
</div>
```

```css
.filter-chips {
  display: flex;
  gap: 8px;
  padding: 12px 0;
  overflow-x: auto;
  scrollbar-width: none;
}
.filter-chips::-webkit-scrollbar { display: none; }
.chip {
  padding: 8px 16px;
  border-radius: var(--radius-full);
  border: 1px solid var(--border-subtle);
  background: var(--bg-card);
  color: var(--text-secondary);
  font-family: inherit;
  font-size: 12px;
  font-weight: 500;
  white-space: nowrap;
  cursor: pointer;
  transition: all var(--transition-base);
}
.chip.active {
  background: var(--accent-blue);
  color: #fff;
  border-color: var(--accent-blue);
}
.feed-card { display: flex; gap: 12px; align-items: center; }
.feed-thumb {
  width: 52px; height: 52px; border-radius: var(--radius-sm);
  flex-shrink: 0;
}
.feed-content { flex: 1; min-width: 0; }
.feed-title { font-size: 13px; font-weight: 600; color: var(--text-primary); }
.feed-subtitle { font-size: 11px; color: var(--text-tertiary); margin-top: 2px; }
.feed-meta { display: flex; align-items: center; gap: 8px; margin-top: 6px; }
.feed-time { font-size: 10px; color: var(--text-tertiary); }
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 24px;
  text-align: center;
  gap: 8px;
}
.empty-icon { font-size: 48px; margin-bottom: 8px; }
.empty-title { font-size: 17px; font-weight: 600; color: var(--text-primary); }
.empty-desc { font-size: 13px; color: var(--text-tertiary); max-width: 240px; margin-bottom: 16px; }
```

### Detail / Product Screen

Key components: hero image, feature list, CTA button group, reviews section.

```html
<!-- Hero Image Area -->
<div class="detail-hero" style="background:var(--gradient-ocean);height:180px;border-radius:0 0 var(--radius-lg) var(--radius-lg);"></div>

<!-- Feature List -->
<div class="feature-list">
  <div class="feature-item">
    <span class="feature-icon" style="background:rgba(10,132,255,0.15);color:var(--accent-blue);">⚡</span>
    <div class="feature-text">
      <div class="feature-name">Lightning Fast</div>
      <div class="feature-desc">Process in under 2 seconds</div>
    </div>
  </div>
  <div class="feature-item">
    <span class="feature-icon" style="background:rgba(48,209,88,0.15);color:var(--accent-green);">🔒</span>
    <div class="feature-text">
      <div class="feature-name">Bank-Level Security</div>
      <div class="feature-desc">256-bit encryption standard</div>
    </div>
  </div>
</div>

<!-- CTA Button Group -->
<div class="cta-group">
  <button class="btn-primary">Get Started — Free</button>
  <button class="btn-secondary">Learn More</button>
</div>

<!-- Reviews Section -->
<div class="review-card glass-card">
  <div class="review-header">
    <div class="review-stars">★★★★★</div>
    <span class="review-date">Jan 2026</span>
  </div>
  <div class="review-body">"Completely changed how I manage my workflow. The AI suggestions are spot-on."</div>
  <div class="review-author">— Sarah M.</div>
</div>
```

```css
.feature-list { display: flex; flex-direction: column; gap: 14px; padding: 16px 0; }
.feature-item { display: flex; align-items: center; gap: 12px; }
.feature-icon {
  width: 40px; height: 40px; border-radius: var(--radius-sm);
  display: flex; align-items: center; justify-content: center;
  font-size: 18px; flex-shrink: 0;
}
.feature-name { font-size: 13px; font-weight: 600; color: var(--text-primary); }
.feature-desc { font-size: 11px; color: var(--text-tertiary); margin-top: 2px; }
.cta-group { display: flex; flex-direction: column; gap: 10px; padding: 16px 0; }
.review-card { padding: 14px; }
.review-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.review-stars { color: var(--accent-yellow); font-size: 14px; letter-spacing: 2px; }
.review-date { font-size: 10px; color: var(--text-tertiary); }
.review-body { font-size: 12px; color: var(--text-secondary); line-height: 1.5; font-style: italic; }
.review-author { font-size: 11px; color: var(--text-tertiary); margin-top: 8px; font-weight: 500; }
```

### Onboarding Screen

Key components: step indicator, illustration area, feature highlight cards, skip/next buttons.

```html
<!-- Step Indicator -->
<div class="onboarding-steps">
  <span class="step-dot active"></span>
  <span class="step-dot"></span>
  <span class="step-dot"></span>
</div>

<!-- Illustration Area -->
<div class="onboarding-illustration" style="background:var(--gradient-cool);height:200px;border-radius:var(--radius-lg);margin:20px 0;display:flex;align-items:center;justify-content:center;">
  <span style="font-size:64px;">🚀</span>
</div>

<!-- Feature Highlight Card -->
<div class="onboarding-content">
  <h2 class="onboarding-title">Track Everything</h2>
  <p class="onboarding-desc">Get real-time insights into your daily habits with AI-powered analytics.</p>
</div>

<!-- Navigation Buttons -->
<div class="onboarding-nav">
  <button class="btn-skip">Skip</button>
  <button class="btn-primary" style="width:auto;padding:14px 40px;">Next</button>
</div>
```

```css
.onboarding-steps { display: flex; justify-content: center; gap: 8px; padding: 16px 0; }
.step-dot {
  width: 8px; height: 8px; border-radius: 50%;
  background: var(--text-tertiary); transition: all var(--transition-base);
}
.step-dot.active {
  width: 24px; border-radius: 4px;
  background: var(--gradient-hero);
}
.onboarding-content { text-align: center; padding: 0 16px; }
.onboarding-title { font-size: 24px; font-weight: 700; color: var(--text-primary); margin-bottom: 8px; }
.onboarding-desc { font-size: 14px; color: var(--text-secondary); line-height: 1.6; max-width: 280px; margin: 0 auto; }
.onboarding-nav {
  display: flex; justify-content: space-between; align-items: center;
  padding: 20px 16px; margin-top: auto;
}
.btn-skip {
  background: none; border: none; color: var(--text-tertiary);
  font-family: inherit; font-size: 14px; cursor: pointer;
  padding: 10px 16px;
}
.btn-skip:hover { color: var(--text-secondary); }
```

### Form / Input Screen

Key components: labeled input groups, validation states, dropdown selectors, date pickers.

```html
<!-- Labeled Input Group -->
<div class="form-group">
  <label class="form-label">Full Name</label>
  <input type="text" class="input-field" placeholder="Enter your name" value="Jane Doe">
</div>

<!-- Validation States -->
<div class="form-group">
  <label class="form-label">Email Address</label>
  <input type="email" class="input-field input-error" placeholder="Enter email" value="not-an-email">
  <span class="form-error">Please enter a valid email address</span>
</div>
<div class="form-group">
  <label class="form-label">Password</label>
  <input type="password" class="input-field input-success" placeholder="Enter password" value="••••••••">
  <span class="form-success">Strong password</span>
</div>

<!-- Dropdown Selector -->
<div class="form-group">
  <label class="form-label">Category</label>
  <div class="select-wrapper">
    <select class="input-field select-field">
      <option>Personal</option>
      <option>Work</option>
      <option>Other</option>
    </select>
    <span class="select-arrow">▾</span>
  </div>
</div>

<!-- Date Picker Row -->
<div class="form-group">
  <label class="form-label">Due Date</label>
  <div class="date-picker-row">
    <button class="date-segment active">Feb</button>
    <button class="date-segment">06</button>
    <button class="date-segment">2026</button>
  </div>
</div>
```

```css
.form-group { margin-bottom: 16px; }
.form-label {
  display: block;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 6px;
}
.input-error { border-color: var(--accent-red) !important; }
.input-error:focus { box-shadow: 0 0 0 4px rgba(255, 69, 58, 0.1) !important; }
.input-success { border-color: var(--accent-green) !important; }
.input-success:focus { box-shadow: 0 0 0 4px rgba(48, 209, 88, 0.1) !important; }
.form-error { font-size: 10px; color: var(--accent-red); margin-top: 4px; display: block; }
.form-success { font-size: 10px; color: var(--accent-green); margin-top: 4px; display: block; }
.select-wrapper { position: relative; }
.select-field {
  appearance: none;
  -webkit-appearance: none;
  padding-right: 36px;
}
.select-arrow {
  position: absolute;
  right: 14px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--text-tertiary);
  pointer-events: none;
  font-size: 14px;
}
.date-picker-row { display: flex; gap: 8px; }
.date-segment {
  flex: 1;
  padding: 12px;
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  color: var(--text-primary);
  font-family: inherit;
  font-size: 14px;
  font-weight: 500;
  text-align: center;
  cursor: pointer;
  transition: all var(--transition-base);
}
.date-segment.active {
  border-color: var(--accent-blue);
  background: rgba(10, 132, 255, 0.1);
  color: var(--accent-blue);
}
```
