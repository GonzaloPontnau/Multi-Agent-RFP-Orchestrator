interface PromptSuggestionsProps {
  onSelect: (prompt: string) => void;
}

const SUGGESTIONS = [
  {
    category: "Resumen",
    prompts: [
      "Resume los puntos clave del documento",
      "Cuales son los requisitos principales",
      "Identifica las fechas limite mencionadas",
    ],
  },
  {
    category: "Analisis",
    prompts: [
      "Que criterios de evaluacion se mencionan",
      "Cuales son los entregables esperados",
      "Identifica los riesgos del proyecto",
    ],
  },
  {
    category: "Detalles",
    prompts: [
      "Cual es el presupuesto estimado",
      "Que experiencia previa se requiere",
      "Cuales son las condiciones de pago",
    ],
  },
];

export function PromptSuggestions({ onSelect }: PromptSuggestionsProps) {
  return (
    <div className="flex-1 flex items-center justify-center p-8">
      <div className="max-w-2xl w-full">
        <div className="text-center mb-10">
          <h2 className="text-2xl font-light text-slate-300 mb-2">
            Consulta tus documentos RFP
          </h2>
          <p className="text-slate-500">
            Selecciona una sugerencia o escribe tu pregunta
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {SUGGESTIONS.map((group) => (
            <div key={group.category} className="space-y-2">
              <h3 className="text-xs font-medium text-slate-500 uppercase tracking-wider px-1">
                {group.category}
              </h3>
              <div className="space-y-2">
                {group.prompts.map((prompt) => (
                  <button
                    key={prompt}
                    onClick={() => onSelect(prompt)}
                    className="w-full text-left p-3 rounded-xl border border-slate-800 hover:border-slate-700 hover:bg-slate-800/50 transition-all group"
                  >
                    <span className="text-sm text-slate-400 group-hover:text-slate-300 transition-colors">
                      {prompt}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
