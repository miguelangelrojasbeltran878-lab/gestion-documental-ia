---
name: Academic Intelligence Interface
colors:
  surface: '#faf8ff'
  surface-dim: '#d9d9e5'
  surface-bright: '#faf8ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f3f3fe'
  surface-container: '#ededf9'
  surface-container-high: '#e7e7f3'
  surface-container-highest: '#e1e2ed'
  on-surface: '#191b23'
  on-surface-variant: '#434655'
  inverse-surface: '#2e3039'
  inverse-on-surface: '#f0f0fb'
  outline: '#737686'
  outline-variant: '#c3c6d7'
  surface-tint: '#0053db'
  primary: '#004ac6'
  on-primary: '#ffffff'
  primary-container: '#2563eb'
  on-primary-container: '#eeefff'
  inverse-primary: '#b4c5ff'
  secondary: '#4b41e1'
  on-secondary: '#ffffff'
  secondary-container: '#645efb'
  on-secondary-container: '#fffbff'
  tertiary: '#943700'
  on-tertiary: '#ffffff'
  tertiary-container: '#bc4800'
  on-tertiary-container: '#ffede6'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#dbe1ff'
  primary-fixed-dim: '#b4c5ff'
  on-primary-fixed: '#00174b'
  on-primary-fixed-variant: '#003ea8'
  secondary-fixed: '#e2dfff'
  secondary-fixed-dim: '#c3c0ff'
  on-secondary-fixed: '#0f0069'
  on-secondary-fixed-variant: '#3323cc'
  tertiary-fixed: '#ffdbcd'
  tertiary-fixed-dim: '#ffb596'
  on-tertiary-fixed: '#360f00'
  on-tertiary-fixed-variant: '#7d2d00'
  background: '#faf8ff'
  on-background: '#191b23'
  surface-variant: '#e1e2ed'
typography:
  display-lg:
    fontFamily: Inter
    fontSize: 48px
    fontWeight: '700'
    lineHeight: '1.2'
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '700'
    lineHeight: '1.25'
    letterSpacing: -0.02em
  headline-lg-mobile:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '700'
    lineHeight: '1.3'
  headline-md:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: '1.3'
  headline-sm:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '600'
    lineHeight: '1.4'
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: '1.6'
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.5'
  body-sm:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: '1.5'
  label-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '600'
    lineHeight: '1'
    letterSpacing: 0.01em
  label-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '500'
    lineHeight: '1'
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  base: 4px
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 32px
  2xl: 48px
  3xl: 64px
  container-max: 1280px
  sidebar-width: 260px
  gutter: 24px
---

## Brand & Style
The design system is centered on the intersection of academic rigor and AI-driven efficiency. The brand personality is professional, authoritative, and helpful, aiming to instill confidence in students and faculty navigating automated support.

The visual style is **Corporate / Modern** with a focus on systematic clarity. It utilizes a highly structured layout, generous negative space, and a refined color palette to reduce cognitive load. The aesthetic avoids unnecessary decoration, favoring functional elements that guide the user toward resolution. The emotional response should be one of "effortless reliability."

## Colors
The color strategy employs a core "Trustworthy Corporate Blue" to establish authority. "Soft Indigo" is used sparingly for secondary interactions and AI-specific features to subtly differentiate human-led and machine-led processes. 

The background uses a cool-toned light gray to define the boundaries of the white surface containers clearly. Semantic colors (Success, Warning, Danger) follow industry standards to ensure immediate recognition of system status and feedback.

## Typography
The design system exclusively uses **Inter** to achieve a neutral, systematic, and utilitarian feel. The hierarchy is established through significant weight shifts rather than just size changes. 

Headlines utilize tighter letter spacing and heavy weights (600-700) to command attention. Body text is optimized for readability with a 1.5x line height. For data-dense views, use `body-sm` and `label-sm` to maintain a professional, organized information density.

## Layout & Spacing
The layout follows a **Fixed Grid** model for desktop, centered within a 1280px container, and a **Fluid Grid** for tablet and mobile devices. 

- **Desktop (1024px+):** 12-column grid, 24px gutters, fixed sidebar.
- **Tablet (768px - 1023px):** 8-column grid, 16px gutters, collapsible sidebar.
- **Mobile (<767px):** 4-column grid, 16px gutters, bottom navigation or hamburger menu.

Spacing is based on an 8px scale. Use `md` (16px) for internal card padding and `lg` (24px) for margins between major layout sections.

## Elevation & Depth
This design system utilizes **Tonal Layers** combined with **Ambient Shadows**. Depth is used purposefully to separate the canvas (background) from interactive objects (cards and modals).

- **Level 0 (Background):** #F8FAFC.
- **Level 1 (Cards/Surface):** White background, 1px border (#E2E8F0), and a subtle shadow (Y: 1px, Blur: 3px, Opacity: 5% Black).
- **Level 2 (Hover states/Dropdowns):** Medium shadow (Y: 4px, Blur: 6px, Opacity: 10% Black).
- **Level 3 (Modals/Overlays):** Large shadow (Y: 10px, Blur: 15px, Opacity: 12% Black).

Shadows should be slightly tinted with the primary blue color (e.g., using a very dark navy instead of pure black at 5-10% opacity) to maintain color harmony.

## Shapes
The shape language is **Rounded**, reflecting a modern and approachable software experience while remaining professional. 

- **Standard Elements:** Buttons, Input fields, and Small Cards use `rounded` (0.5rem / 8px).
- **Containers:** Large content blocks and Data Tables use `rounded-lg` (1rem / 16px).
- **AI Chat Bubbles:** Use `rounded-xl` (1.5rem / 24px) to distinguish conversational UI from the rest of the structured interface.

## Components
### Buttons
- **Primary:** Solid #2563EB, white text, 8px radius. High emphasis.
- **Secondary:** Border 1px #CBD5E1, white background, #1E293B text. Medium emphasis.
- **Ghost:** No border, primary color text. Low emphasis for utility actions.

### Sidebar Navigation
The sidebar should use a persistent light-gray or white background with a 1px right border. Active states are indicated by a 4px vertical primary-blue bar on the left and a light blue background-fill behind the icon and text.

### Cards & Metrics
Metric cards feature a large `headline-lg` value and a `label-sm` title. Use subtle icons in the top right corner to categorize the metric.

### Tables
Tables must have a 1px border (#E2E8F0) and rounded corners (16px). The header row should have a light gray background (#F1F5F9) to separate it from the data rows.

### Form Inputs
Inputs use a white background, 1px #CBD5E1 border, and transition to a 2px #2563EB border on focus with a soft blue outer glow.

### AI Chat Interface
AI-generated responses should be contained within a slightly tinted Indigo (#F5F3FF) bubble to visually separate them from user queries (white bubbles). Include "helpful/not-helpful" feedback icons at the bottom of each AI response.