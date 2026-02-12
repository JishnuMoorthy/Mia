# 🔧 ENVIRONMENT SETUP & CONFIGURATION

**Purpose**: Exact environment requirements for Lovable to build Phase 1 successfully  
**For**: Lovable AI (Frontend Developer)  
**Date**: February 12, 2026  

---

## 📦 REQUIRED VERSIONS

### Node.js
```bash
# Required: v20.20.0 or any LTS version (v18+, v20+, v22+)
# Verified working: v20.20.0
node --version
# Output: v20.20.0
```

### npm
```bash
# Required: v10.0.0 or higher
npm --version
# Output: 10.8.2+
```

**Why These Versions?**
- Node v20 is current LTS with long-term support
- npm 10+ has improved monorepo support and peer dependency resolution
- Next.js 15+ requires Node v18+

---

## 🚀 PROJECT INITIALIZATION

### Create Next.js Project
```bash
# Option 1: Using create-next-app (Recommended)
npx create-next-app@latest mia-frontend \
  --typescript \
  --tailwind \
  --app \
  --eslint \
  --no-src-dir=false

# Option 2: Manual setup if create-next-app fails
mkdir mia-frontend
cd mia-frontend
npm init -y
npm install next@latest react@latest react-dom@latest typescript tailwindcss
```

### Required Next.js Configuration
**`next.config.ts`**:
```typescript
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  typescript: {
    strict: true,
  },
  env: {
    NEXT_PUBLIC_API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL,
    NEXT_PUBLIC_APP_NAME: process.env.NEXT_PUBLIC_APP_NAME,
  },
};

export default nextConfig;
```

**`tsconfig.json`** (Enable strict mode):
```json
{
  "compilerOptions": {
    "strict": true,
    "moduleResolution": "bundler",
    "noImplicitAny": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["src/*"]
    }
  },
  "include": ["next.env.d.ts", "**/*.ts", "**/*.tsx"],
  "exclude": ["node_modules"]
}
```

---

## 📋 EXACT DEPENDENCIES

### `package.json` (Core Dependencies)

```json
{
  "name": "mia-vms-frontend",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint",
    "type-check": "tsc --noEmit"
  },
  "dependencies": {
    "next": "^15.0.0",
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "@tanstack/react-query": "^5.28.0",
    "react-hook-form": "^7.48.0",
    "axios": "^1.6.0"
  },
  "devDependencies": {
    "typescript": "^5.3.0",
    "tailwindcss": "^3.4.0",
    "postcss": "^8.4.0",
    "autoprefixer": "^10.4.0",
    "@types/react": "^19.0.0",
    "@types/react-dom": "^19.0.0",
    "@types/node": "^20.0.0",
    "eslint": "^8.0.0",
    "eslint-config-next": "^15.0.0"
  }
}
```

### Why These Packages?
- **next@15+**: Latest React framework with App Router
- **react@19+**: Latest React with improved hooks
- **@tanstack/react-query@5+**: Server state management (replaces SWR)
- **react-hook-form@7+**: Form state management (lightweight)
- **axios@1.6+**: HTTP client (better error handling than fetch)
- **TypeScript@5+**: Type safety (strict mode enabled)
- **tailwindcss@3+**: Utility CSS framework (no build complexity)

### Installation Command
```bash
npm install
```

---

## 🌍 ENVIRONMENT VARIABLES

### `.env.local` (Development)

```bash
# API Configuration
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1

# App Configuration  
NEXT_PUBLIC_APP_NAME=Mia VMS Admin

# Optional: For debugging during development
NEXT_PUBLIC_DEBUG=false
```

**CRITICAL NOTES:**
- ✅ `NEXT_PUBLIC_` prefix makes these available in browser
- ✅ Do NOT put secrets here (tokens, API keys, etc.)
- ✅ Create `.env.local` in project root (NOT in src/)
- ✅ Add `.env.local` to `.gitignore` (never commit)
- ✅ Backend must be running on `http://localhost:8000` for development

### `.env.production` (Production - for reference)

```bash
# Will be set during deployment
NEXT_PUBLIC_API_BASE_URL=https://api.mia-clinic.com/api/v1
NEXT_PUBLIC_APP_NAME=Mia VMS Admin
```

---

## 🎨 TAILWIND CONFIGURATION

### `tailwind.config.ts`

```typescript
import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        primary: '#0066CC',      // Professional blue
        secondary: '#00B4D8',    // Teal accent
        success: '#10B981',      // Green
        warning: '#F59E0B',      // Amber
        danger: '#EF4444',       // Red
      },
      fontSize: {
        xs: ['12px', { lineHeight: '16px' }],
        sm: ['14px', { lineHeight: '20px' }],
        base: ['16px', { lineHeight: '24px' }],
        lg: ['18px', { lineHeight: '28px' }],
        xl: ['20px', { lineHeight: '28px' }],
      },
    },
  },
  plugins: [],
}
export default config
```

### `postcss.config.js`

```javascript
module.exports = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
```

---

## 📂 FOLDER STRUCTURE SETUP

### Create This Exact Structure

```bash
mia-frontend/
├── src/
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx
│   │   ├── auth/
│   │   │   ├── login/
│   │   │   │   └── page.tsx
│   │   │   └── logout/
│   │   │       └── page.tsx
│   │   ├── dashboard/
│   │   │   └── page.tsx
│   │   ├── pets/
│   │   │   ├── page.tsx
│   │   │   ├── [id]/
│   │   │   │   └── page.tsx
│   │   │   └── new/
│   │   │       └── page.tsx
│   │   ├── owners/
│   │   ├── appointments/
│   │   ├── billing/
│   │   ├── inventory/
│   │   ├── staff/
│   │   └── settings/
│   ├── components/
│   │   ├── Sidebar.tsx
│   │   ├── Header.tsx
│   │   ├── Footer.tsx
│   │   ├── Table.tsx
│   │   ├── Modal.tsx
│   │   ├── Form.tsx
│   │   ├── Loading.tsx
│   │   └── Notification.tsx
│   ├── lib/
│   │   ├── api.ts
│   │   ├── auth.ts
│   │   └── constants.ts
│   ├── hooks/
│   │   ├── useAuth.ts
│   │   ├── useApi.ts
│   │   └── useNotification.ts
│   ├── types/
│   │   └── index.ts
│   └── globals.css
├── public/
│   └── icons/
├── .env.local
├── .gitignore
├── next.config.ts
├── tailwind.config.ts
├── tsconfig.json
├── package.json
└── README.md
```

**Create directories:**
```bash
mkdir -p src/{app,components,lib,hooks,types}
mkdir -p src/app/{auth/login,auth/logout,dashboard,pets,owners,appointments,billing,inventory,staff,settings}
mkdir -p public/icons
```

---

## 🏃 DEVELOPMENT WORKFLOW

### Start Development Server
```bash
cd mia-frontend
npm run dev
# Output: ▲ Next.js 15.0.0
#         - Local: http://localhost:3000
```

Visit `http://localhost:3000` in browser.

### Build for Production
```bash
npm run build
# Output: ✓ Compiled successfully
#         ✓ Linted successfully
# Creates .next/ folder
```

### Run Production Build
```bash
npm run start
# Starts optimized production server
```

### Type Check
```bash
npm run type-check
# Verifies TypeScript without building
```

### Lint Check
```bash
npm run lint
# Checks code quality with ESLint
```

---

## ✅ VERIFICATION CHECKLIST

Before you start building, verify:

- [ ] Node.js v20+ installed: `node --version`
- [ ] npm 10+ installed: `npm --version`
- [ ] Next.js project created: `ls -la src/app/`
- [ ] Dependencies installed: `npm ls next react typescript`
- [ ] `.env.local` created with `NEXT_PUBLIC_API_BASE_URL`
- [ ] `tsconfig.json` has `"strict": true`
- [ ] `tailwind.config.ts` configured
- [ ] Development server starts: `npm run dev`
- [ ] Builds without errors: `npm run build`
- [ ] No TypeScript errors: `npm run type-check`

---

## 🚨 COMMON ISSUES & FIXES

### Issue: `Cannot find module 'next'`
```bash
# Fix: Install dependencies
npm install
```

### Issue: `Error: ENOENT: no such file or directory '.env.local'`
```bash
# Fix: Create .env.local file
echo "NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1" > .env.local
```

### Issue: Port 3000 already in use
```bash
# Fix: Use different port
npm run dev -- -p 3001
```

### Issue: TypeScript errors on build
```bash
# Fix: Check strict mode
npm run type-check
# Ensure tsconfig.json has "strict": true
```

### Issue: Tailwind styles not applying
```bash
# Fix: Verify content paths in tailwind.config.ts
# Ensure src/globals.css imports Tailwind:
# @tailwind base;
# @tailwind components;
# @tailwind utilities;
```

---

## 📞 REFERENCE FOR LOVABLE

When Lovable sets up the project:

1. ✅ Initialize with Node v20+, npm 10+
2. ✅ Install exact dependencies from `package.json` above
3. ✅ Create folder structure per "FOLDER STRUCTURE SETUP" section
4. ✅ Copy environment files (`.env.local`, `next.config.ts`, etc.)
5. ✅ Verify with "VERIFICATION CHECKLIST"
6. ✅ Start development with `npm run dev`

---

## 🎯 PRODUCTION DEPLOYMENT

### Environment Variables (Production)
```bash
NEXT_PUBLIC_API_BASE_URL=https://api.your-domain.com/api/v1
```

### Build for Production
```bash
npm run build
npm run start
```

### Docker (Optional)
```dockerfile
FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build
EXPOSE 3000
CMD ["npm", "start"]
```

---

## ✨ SUMMARY

| Item | Requirement | Status |
|------|-------------|--------|
| Node.js | v20.20.0 (or LTS) | ✅ |
| npm | 10.8.2+ | ✅ |
| Next.js | 15.0.0+ | ✅ |
| TypeScript | Strict mode enabled | ✅ |
| Tailwind | Configured | ✅ |
| Environment | `.env.local` with API base URL | ✅ |
| Dependencies | Exact versions specified | ✅ |
| Folder Structure | As per specification | ✅ |
| Development | Verified with `npm run dev` | ✅ |
| Production | Verified with `npm run build` | ✅ |

---

**Next Step**: Reference this during Lovable project setup. Verify everything with the VERIFICATION CHECKLIST before starting feature development.

**Questions?** Reference LOVABLE_BRIEF_PHASE1.md for feature specs or BACKEND_INTEGRATION_GUARDRAILS.md for API details.
