# MiniDani Agents

**Nota:** Estos archivos son **templates de referencia** para sistemas multi-agente jerárquicos.

OpenCode actualmente no soporta este tipo de agentes custom (solo tiene "Search Agent" builtin). 

## Uso Actual

Los agentes están aquí documentados como:
- **Referencia de arquitectura** para entender cómo funciona MiniDani
- **Templates** para adaptar a otras herramientas (Aider, Claude Code)
- **Documentación** del diseño del sistema

## Implementación Real

El sistema MiniDani actual está implementado como **script Python orquestador** (`minidani.py`) que:
1. Llama a OpenCode/Claude API directamente
2. Maneja worktrees y git operations
3. Coordina el flujo completo

Los agentes aquí describen **cómo debería funcionar** un sistema multi-agente ideal, pero la ejecución actual es vía orquestación de script.

## Agentes Definidos

- `minidani.md` - Orchestrator principal
- `minidani-manager.md` - Manager de equipo
- `minidani-employee-red.md` - Implementador
- `minidani-employee-blue.md` - Verificador
- `minidani-product-manager.md` - Juez
- `minidani-pr-creator.md` - Creador de PR

Estos definen la **arquitectura lógica**, aunque la ejecución es via Python script.
