# PoliMilpa Web

Frontend en Next.js para la capa visual principal de PoliMilpa.

## Qué hace
- Navbar con marca, navegación e inicio de sesión
- Hero con selección de zonas por regiones
- Leyenda de colores agroclimáticos
- Espacio para el mapa y la vista mobile

## Cómo correrlo

```bash
cd web
npm install
npm run dev
```

Por defecto consume la API en `http://localhost:8000`.

## Backend Python

El backend FastAPI sigue en la raíz del repo y no cambia de stack. Solo se agregó CORS para desarrollo local desde `http://localhost:3000`.
