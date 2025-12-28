# React TypeScript Client

A modern React application built with TypeScript, Vite, Tailwind CSS, and shadcn/ui components.

## 🚀 Tech Stack

- **React 19** - UI library
- **TypeScript** - Type safety
- **Vite** - Build tool and dev server
- **Tailwind CSS v4** - Utility-first CSS framework
- **shadcn/ui** - High-quality component library
- **Lucide React** - Icon library

## 📦 Prerequisites

- Node.js 18+ and npm/yarn/pnpm
- (Optional) Cursor IDE with shadcn MCP support for enhanced component management

## 🛠️ Installation

1. Install dependencies:
```bash
npm install
# or
yarn install
# or
pnpm install
```

## 🏃 Development

Start the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
```

The app will be available at `http://localhost:5173` (or the next available port).

## 🏗️ Building

Build for production:

```bash
npm run build
# or
yarn build
# or
pnpm build
```

Preview the production build:

```bash
npm run preview
# or
yarn preview
# or
pnpm preview
```

## 📁 Project Structure

```
client/
├── src/
│   ├── components/     # React components
│   │   └── ui/        # shadcn/ui components
│   ├── lib/           # Utility functions
│   │   └── utils.ts   # cn() helper for className merging
│   ├── hooks/         # Custom React hooks
│   ├── App.tsx        # Main app component
│   ├── main.tsx       # Entry point
│   └── index.css      # Global styles & Tailwind imports
├── components.json    # shadcn/ui configuration
├── package.json       # Dependencies and scripts
└── vite.config.ts     # Vite configuration
```

## 🎨 Using shadcn/ui Components

This project is configured with shadcn/ui and supports MCP (Model Context Protocol) integration with Cursor IDE.

### Adding Components via CLI

```bash
npx shadcn@latest add [component-name]
```

Example:
```bash
npx shadcn@latest add button
npx shadcn@latest add card
npx shadcn@latest add dialog
```

### Adding Components via Cursor MCP

This project supports the [shadcn MCP server](https://github.com/AshMartian/shadcn-mcp-server) for Cursor IDE integration. To enable:

1. Add the shadcn MCP server to your Cursor settings (`.cursor/mcp.json`):
```json
{
  "mcpServers": {
    "shadcn": {
      "command": "npx",
      "args": ["-y", "shadcn-mcp-server@latest"]
    }
  }
}
```

2. Restart Cursor to activate the MCP server

3. Now you can ask Cursor's AI to add shadcn components directly:
   - "Add a dialog component"
   - "Install the dropdown-menu component"
   - "Add button, card, and input components"

Components will be automatically added to `src/components/ui/` with proper TypeScript types and Tailwind styling.

### Available Component Aliases

- `@/components` - Your custom components
- `@/components/ui` - shadcn/ui components
- `@/lib/utils` - Utility functions (includes `cn()` helper)
- `@/lib` - Library utilities
- `@/hooks` - Custom React hooks

### Example Usage

```tsx
import { Button } from "@/components/ui/button"
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card"
import { cn } from "@/lib/utils"

function MyComponent() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Hello World</CardTitle>
        <CardDescription>This is a shadcn/ui card component</CardDescription>
      </CardHeader>
      <CardContent>
        <Button className={cn("w-full")}>Click me</Button>
      </CardContent>
    </Card>
  )
}
```

## 🎯 Configuration

### Tailwind CSS

Tailwind CSS v4 is configured via `@tailwindcss/vite` plugin. Global styles and CSS variables are defined in `src/index.css`.

### TypeScript

TypeScript is configured with strict mode enabled. Path aliases are set up for clean imports:
- `@/*` maps to `./src/*`

### shadcn/ui

Configuration is in `components.json`:
- **Style**: New York
- **Base Color**: Neutral
- **CSS Variables**: Enabled
- **Icon Library**: Lucide React
- **MCP Support**: Configured for Cursor IDE integration

## 📝 Code Style

- ESLint is configured for code quality
- TypeScript strict mode is enabled
- Follow React best practices and hooks rules

## 🔧 Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint

## 📚 Learn More

- [React Documentation](https://react.dev)
- [Vite Documentation](https://vite.dev)
- [Tailwind CSS Documentation](https://tailwindcss.com)
- [shadcn/ui Documentation](https://ui.shadcn.com)
- [TypeScript Documentation](https://www.typescriptlang.org)

## 🤝 Contributing

When adding new features:
1. Create components in `src/components/`
2. Use shadcn/ui components from `src/components/ui/`
3. Add custom hooks to `src/hooks/`
4. Keep utility functions in `src/lib/`
5. Follow TypeScript best practices

## 📄 License

This project is part of the ACL Anthology RAG application.

