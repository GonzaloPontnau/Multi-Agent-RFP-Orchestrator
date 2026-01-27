interface PromptSuggestionsProps {
  onSelect: (prompt: string) => void;
}

const SUGGESTIONS = [
  {
    category: "Resumen",
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
    ),
    prompts: [
      "Resume los puntos clave del documento",
      "Cuales son los requisitos principales",
      "Identifica las fechas limite mencionadas",
    ],
  },
  {
    category: "Analisis",
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
      </svg>
    ),
    prompts: [
      "Que criterios de evaluacion se mencionan",
      "Cuales son los entregables esperados",
      "Identifica los riesgos del proyecto",
    ],
  },
  {
    category: "Detalles",
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
      </svg>
    ),
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
      <div className="max-w-3xl w-full">
        {/* Header */}
        <div className="text-center mb-12">
          <div className="relative inline-block mb-6">
            <div className="absolute inset-0 bg-orange-500/20 rounded-full blur-2xl scale-150" />
            <img 
              src="/logo.png" 
              alt="RFP Orchestrator" 
              className="relative w-20 h-20 rounded-full ring-2 ring-orange-500/20"
            />
          </div>
          <h2 className="text-2xl font-light text-slate-200 mb-2">
            Consulta tus documentos RFP
          </h2>
          <p className="text-slate-500">
            Selecciona una sugerencia o escribe tu pregunta
          </p>
        </div>

        {/* Suggestions Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {SUGGESTIONS.map((group) => (
            <div key={group.category} className="space-y-3">
              <div className="flex items-center gap-2 px-1 text-slate-500">
                {group.icon}
                <h3 className="text-xs font-medium uppercase tracking-wider">
                  {group.category}
                </h3>
              </div>
              <div className="space-y-2">
                {group.prompts.map((prompt) => (
                  <button
                    key={prompt}
                    onClick={() => onSelect(prompt)}
                    className="w-full text-left p-4 rounded-2xl bg-slate-800/30 border border-slate-800/50 hover:bg-slate-800/50 hover:border-slate-700/50 hover:scale-[1.02] transition-all duration-200 group"
                  >
                    <span className="text-sm text-slate-400 group-hover:text-slate-300 transition-colors leading-relaxed">
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
