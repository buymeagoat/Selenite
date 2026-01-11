# Selenite Frontend

React 18 + Vite + TypeScript frontend for Selenite transcription application.

## Setup

```bash
npm install
npm run start:prod
```

## Available Scripts

- `npm run start:prod` - Build and serve the production bundle on http://127.0.0.1:5174
- `npm run build` - Build for production  
- `npm test` - Run tests with Vitest
- `npm run test:watch` - Run tests in watch mode
- `npm run lint` - Lint code with ESLint
- `npm run preview` - Preview production build

## Tech Stack

- React 18
- TypeScript
- Vite
- React Router v6
- Tailwind CSS (pine forest theme)
- Axios
- Vitest + Testing Library

## Project Structure

```
src/
├── components/
│   └── layout/
│       ├── Navbar.tsx
│       └── ProtectedRoute.tsx
├── context/
│   └── AuthContext.tsx
├── pages/
│   └── Login.tsx
├── tests/
│   ├── setup.ts
│   ├── Login.test.tsx
│   ├── ProtectedRoute.test.tsx
│   └── Navbar.test.tsx
├── App.tsx
├── main.tsx
├── router.tsx
└── index.css
```

