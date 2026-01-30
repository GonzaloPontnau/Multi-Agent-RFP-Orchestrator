interface PromptSuggestionsProps {
  onSelect: (prompt: string) => void;
}

const SUGGESTIONS = [
  {
    category: "Legal y Normativo",
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 6l3 1m0 0l-3 9a5.002 5.002 0 006.001 0M6 7l3 9M6 7l6-2m6 2l3-1m-3 1l-3 9a5.002 5.002 0 006.001 0M18 7l3 9m-3-9l-6-2m0-2v2m0 16V5m0 16H9m3 0h3" />
      </svg>
    ),
    prompts: [
      "Que sanciones aplican por incumplimiento de plazos o entregables?",
      "Cuales son las clausulas de confidencialidad y propiedad intelectual?",
      "Bajo que jurisdiccion y normativa se rige esta licitacion?",
    ],
  },
  {
    category: "Financiero",
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
    prompts: [
      "Cual es el presupuesto oficial y desglose por componentes?",
      "Que garantias financieras se exigen (seriedad, cumplimiento, anticipo)?",
      "Como es el esquema de pagos y existen clausulas de reajuste de precios?",
    ],
  },
  {
    category: "Tecnico y Requisitos",
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
      </svg>
    ),
    prompts: [
      "Que experiencia previa y certificaciones se requieren para participar?",
      "Cual es el perfil del personal clave exigido y sus requisitos minimos?",
      "Cuales son los SLAs, especificaciones tecnicas o estandares requeridos?",
    ],
  },
  {
    category: "Cronograma",
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
      </svg>
    ),
    prompts: [
      "Cuales son las fechas clave: consultas, apertura de sobres y adjudicacion?",
      "Cual es el plazo de ejecucion del contrato y sus fases principales?",
      "Hay hitos intermedios con entregables obligatorios?",
    ],
  },
  {
    category: "Evaluacion",
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
    prompts: [
      "Como se pondera la evaluacion tecnica vs economica?",
      "Que criterios determinan la descalificacion de una oferta?",
      "Cuales son los factores de desempate entre oferentes?",
    ],
  },
  {
    category: "Analisis Cruzado",
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
      </svg>
    ),
    prompts: [
      "Genera un resumen ejecutivo con requisitos, presupuesto y fechas clave",
      "Identifica los principales riesgos legales, tecnicos y financieros",
      "Que documentos y certificaciones debo preparar para presentar oferta?",
    ],
  },
];

export function PromptSuggestions({ onSelect }: PromptSuggestionsProps) {
  return (
    <div className="flex-1 overflow-y-auto p-8">
      <div className="max-w-5xl w-full mx-auto pb-8">
        {/* Header */}
        <div className="text-center mb-12">
          <div className="relative inline-block mb-6">
            <div className="absolute inset-0 bg-orange-500/20 rounded-full blur-2xl scale-150" />
            <img
              src="/logo.png"
              alt="TenderCortex"
              className="relative w-20 h-20 rounded-full ring-2 ring-orange-500/20"
            />
          </div>
          <h2 className="text-2xl font-light text-slate-200 mb-2">
            Analiza documentos de licitacion
          </h2>
          <p className="text-slate-500">
            Selecciona una consulta o escribe tu pregunta
          </p>
        </div>

        {/* Suggestions Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
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
