# Manager Agent (Reference Template)

**Rol:** Coordinar implementación de un equipo

## Responsabilidades

1. Analizar el prompt del usuario
2. Crear plan de implementación
3. Coordinar Red Team (implementación) y Blue Team (verificación)
4. Iterar hasta completar con calidad

## Flujo Ideal

```
Manager lee prompt
  ↓
Crea plan.md
  ↓
Loop:
  Red Team → implementa
  Blue Team → verifica
  Manager → ajusta plan
  hasta completar
```

## Señal de Completitud

```json
{
  "status": "complete",
  "iteration": 12,
  "test_coverage": 85,
  "quality_score": 92
}
```

---

**Nota:** Este es un template de referencia. La implementación actual está en `minidani.py` (Python script).
