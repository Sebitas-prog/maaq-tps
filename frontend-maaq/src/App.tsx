import {
  AlertTriangle,
  BriefcaseBusiness,
  Building2,
  CalendarClock,
  CheckCircle2,
  ChevronDown,
  ClipboardCheck,
  Download,
  FileText,
  HardHat,
  LayoutDashboard,
  LogIn,
  LogOut,
  RefreshCw,
  Save,
  Search,
  ShieldCheck,
  UserRoundPlus,
  Users,
  WalletCards
} from "lucide-react";
import { FormEvent, ReactNode, useEffect, useMemo, useRef, useState } from "react";
import { API_URL, CatalogItem, Catalogs, api } from "./api";

type Row = Record<string, unknown>;
type ModuleId = "dashboard" | "contratacion" | "contratos" | "asistencia" | "reportes";

type RrhhDashboardData = {
  kpis: Row;
  semaforo: Row[];
  ultimos_contratos: Row[];
};

type RrhhReportes = {
  personal_activo: Row[];
  planilla_total: Row[];
  contratos_por_vencer: Row[];
};

type DocumentoGenerado = {
  tipo: string;
  filename: string;
  html: string;
  data: Row;
};

type ObraOption = {
  id?: number | null;
  IDproyecto?: number | null;
  NombreObra: string;
  label: string;
  Origen?: string;
  TotalContratos?: number;
};

type ChartDatum = {
  label: string;
  value: number;
  color?: string;
};

type LoginResponse = {
  token: string;
  usuario: {
    id: number;
    nombre: string;
    email: string;
    rol: string;
  };
};

const modules: Array<{ id: ModuleId; label: string; icon: ReactNode }> = [
  { id: "dashboard", label: "Inicio", icon: <LayoutDashboard size={18} /> },
  { id: "contratacion", label: "Contratacion", icon: <UserRoundPlus size={18} /> },
  { id: "contratos", label: "Contratos", icon: <CalendarClock size={18} /> },
  { id: "asistencia", label: "Asistencia", icon: <ClipboardCheck size={18} /> },
  { id: "reportes", label: "Reportes", icon: <FileText size={18} /> }
];

const moduleMenus: Record<ModuleId, Array<{ label: string; detail: string }>> = {
  dashboard: [
    { label: "Dashboard principal", detail: "Plantilla activa, alertas y planilla" },
    { label: "Mapa de flujo", detail: "Tres modulos RRHH conectados" },
    { label: "Acciones globales", detail: "Busqueda, historial y exportacion" }
  ],
  contratacion: [
    { label: "Nuevo empleado", detail: "Admin llena el formulario" },
    { label: "Validacion", detail: "DNI unico y campos completos" },
    { label: "Reporte de altas", detail: "Empleado guardado con contrato" }
  ],
  contratos: [
    { label: "Lista semaforo", detail: "Verde, amarillo y rojo" },
    { label: "Acciones", detail: "Renovar, liquidar o revisar detalle" },
    { label: "Vigencia y bajas", detail: "Alertas por vencimiento" }
  ],
  asistencia: [
    { label: "Registrar asistencia", detail: "Fecha, obra y trabajador" },
    { label: "Ingresar destajo", detail: "Partida, metrado y tarifa" },
    { label: "Planilla", detail: "Jornal, destajo y extras" }
  ],
  reportes: [
    { label: "Personal activo", detail: "Por obra y contrato vigente" },
    { label: "Planilla total", detail: "Exportacion Excel y PDF" },
    { label: "Historial", detail: "Cambios auditados" }
  ]
};

const toInputDate = (value: Date) => {
  const local = new Date(value.getTime() - value.getTimezoneOffset() * 60000);
  return local.toISOString().slice(0, 10);
};

const today = () => toInputDate(new Date());

const addDays = (days: number) => {
  const value = new Date();
  value.setDate(value.getDate() + days);
  return toInputDate(value);
};

const AREA_OPTIONS = [
  "Gerencia",
  "Administracion",
  "Recursos Humanos",
  "Operaciones",
  "Logistica",
  "Ingenieria y Planeamiento",
  "Ejecucion de Obras",
  "Seguridad y Salud"
];

const AREA_SALARIOS_MENSUALES: Record<string, number> = {
  gerencia: 4500,
  administracion: 2300,
  "recursos humanos": 2500,
  operaciones: 2800,
  logistica: 2200,
  "ingenieria y planeamiento": 3500,
  "ejecucion de obras": 3000,
  "seguridad y salud": 2600
};

const emptyContratacion = {
  id_tipo_documento: "1",
  numero_documento: "",
  apellido_paterno: "",
  apellido_materno: "",
  nombres: "",
  email: "",
  celular: "",
  id_tipo_empleado: "",
  area: "",
  id_proyecto: "",
  obra: "",
  cargo: "",
  fecha_inicio: today(),
  fecha_fin: addDays(30),
  salario_diario: "60.00"
};

const emptyBoleta = {
  id_contrato: "",
  fecha_cese: today(),
  motivo: "renuncia"
};

const emptyAsistencia = {
  id_empleado: "",
  id_contrato: "",
  fecha: today(),
  obra: "",
  estado: "presente",
  horas: "8.00",
  extras: "0.00",
  observacion: ""
};

const emptyDestajo = {
  id_empleado: "",
  id_contrato: "",
  fecha: today(),
  obra: "",
  partida: "",
  metrado: "",
  tarifa: "",
  observacion: ""
};

const emptyEditEmpleado = {
  id_empleado: "",
  numero_documento: "",
  nombres: "",
  apellido_paterno: "",
  apellido_materno: "",
  email: "",
  celular: "",
  area: ""
};

const emptyReporte = {
  tipo: "contratos",
  area: "",
  estado: "",
  desde: "",
  hasta: "",
  mes_pago: today().slice(0, 7),
  q: "",
  dias: "30",
  limit: "1000"
};

const reporteTipos = [
  { value: "contratos", label: "Contratos generales" },
  { value: "contratos_activos", label: "Contratos activos" },
  { value: "contratos_vencidos", label: "Contratos vencidos" },
  { value: "contratos_por_vencer", label: "Contratos por vencer" },
  { value: "empleados_area", label: "Empleados por area" },
  { value: "ingresantes_rango", label: "Ingresantes por rango" },
  { value: "planilla_rango", label: "Planilla por rango" },
  { value: "asistencia_mes_pago", label: "Asistencia por mes de pago" }
];

const asistenciaEstados = [
  { value: "presente", label: "Presente" },
  { value: "tardanza", label: "Tardanza" },
  { value: "inasistencia", label: "Falta" },
  { value: "permiso", label: "Permiso" },
  { value: "descanso", label: "Descanso" }
];

const companyFacts = [
  { label: "Organizacion", value: "Constructora MAAQ Arquitectos e Ingenieros S.A.C." },
  { label: "Ubicacion", value: "Tingo Maria, provincia de Leoncio Prado, Peru" },
  { label: "Especialidad", value: "Arquitectura, ingenieria y construccion civil" },
  { label: "Sistema", value: "TPS para control de personal, contratos, asistencia y destajo" }
];

const companyPurpose = [
  {
    title: "Mision",
    body:
      "Brindar servicios integrales de arquitectura, ingenieria y construccion civil para desarrollar infraestructura local de calidad, gestionando proyectos con control operativo, trazabilidad y uso eficiente de recursos."
  },
  {
    title: "Vision",
    body:
      "Ser una constructora referente en la selva alta peruana por ejecutar obras confiables, sostenibles y bien documentadas, apoyada en procesos BPM estandarizados y mejora continua."
  }
];

const bpmFocus = [
  "Contratacion con DNI unico y contrato generado.",
  "Control de contratos con alertas por vencimiento.",
  "Asistencia y destajo integrados a planilla."
];

const CHART_COLORS = ["#ff3f62", "#0f766e", "#f59e0b", "#2563eb", "#7c3aed", "#14b8a6", "#ef4444", "#64748b"];

function asNumber(value: string) {
  return Number(value);
}

function optionalNumber(value: string) {
  return value.trim() ? Number(value) : undefined;
}

function optionalText(value: string) {
  return value.trim() ? value.trim() : null;
}

function formatValue(value: unknown) {
  if (value === null || value === undefined || value === "") return "-";
  if (typeof value === "number") return value.toLocaleString("es-PE");
  return String(value);
}

function numericValue(value: unknown) {
  const numberValue = Number(value ?? 0);
  return Number.isFinite(numberValue) ? numberValue : 0;
}

function countLabel(count: number) {
  return `${count} registro${count === 1 ? "" : "s"}`;
}

function areaLabel(row: Row) {
  const value = String(row.Area ?? row.area ?? "Sin area").trim();
  return value || "Sin area";
}

function areaRank(area: string) {
  const index = AREA_OPTIONS.findIndex((item) => item.toLowerCase() === area.toLowerCase());
  return index === -1 ? AREA_OPTIONS.length : index;
}

function salarioMensualArea(area: string) {
  return AREA_SALARIOS_MENSUALES[area.trim().toLowerCase()] ?? 1800;
}

function salarioDiarioArea(area: string) {
  return (salarioMensualArea(area) / 30).toFixed(2);
}

function obraOptionKey(item: ObraOption) {
  return item.IDproyecto ? `proyecto:${item.IDproyecto}` : `obra:${item.NombreObra}`;
}

function formatMoney(value: number) {
  return value.toLocaleString("es-PE", { style: "currency", currency: "PEN" });
}

function shortLabel(value: string, maxLength = 18) {
  return value.length > maxLength ? `${value.slice(0, maxLength - 1)}...` : value;
}

function groupRowsByArea(rows: Row[]) {
  const grouped = new Map<string, Row[]>();
  rows.forEach((row) => {
    const area = areaLabel(row);
    grouped.set(area, [...(grouped.get(area) ?? []), row]);
  });
  return Array.from(grouped.entries()).sort(([areaA], [areaB]) => {
    const rankDiff = areaRank(areaA) - areaRank(areaB);
    return rankDiff || areaA.localeCompare(areaB);
  });
}

function Field({ label, children, wide = false, className = "" }: { label: string; children: ReactNode; wide?: boolean; className?: string }) {
  const classes = [wide ? "field field--wide" : "field", className].filter(Boolean).join(" ");
  return (
    <label className={classes}>
      <span>{label}</span>
      {children}
    </label>
  );
}

function CatalogField({
  label,
  value,
  onChange,
  items,
  required = true
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  items?: CatalogItem[];
  required?: boolean;
}) {
  if (!items?.length) {
    return (
      <Field label={label}>
        <input value={value} onChange={(event) => onChange(event.target.value)} type="number" min="1" required={required} />
      </Field>
    );
  }

  return (
    <Field label={label}>
      <select value={value} onChange={(event) => onChange(event.target.value)} required={required}>
        {!required && <option value="">Sin asignar</option>}
        {items.map((item) => (
          <option key={item.id} value={item.id}>
            {item.label}
          </option>
        ))}
      </select>
    </Field>
  );
}

function SemaforoBadge({ value }: { value: unknown }) {
  const color = String(value || "verde");
  return <span className={`semaforo semaforo--${color}`}>{color}</span>;
}

function DataTable({
  columns,
  rows,
  empty
}: {
  columns: Array<{ key: string; label: string; render?: (row: Row) => ReactNode }>;
  rows: Row[];
  empty: string;
}) {
  if (!rows.length) return <div className="empty">{empty}</div>;

  return (
    <div className="table-shell">
      <table>
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column.key}>{column.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={`${columns[0]?.key}-${index}`}>
              {columns.map((column) => (
                <td key={column.key}>{column.render ? column.render(row) : formatValue(row[column.key])}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function contractOptionLabel(row: Row) {
  return `${formatValue(row.CodigoContrato)} - ${formatValue(row.Empleado)} - ${formatValue(row.Obra)}`;
}

function ContractSearchField({
  id,
  label,
  value,
  contratos,
  onChange
}: {
  id: string;
  label: string;
  value: string;
  contratos: Row[];
  onChange: (idContrato: string) => void;
}) {
  const selected = contratos.find((item) => String(item.IDcontrato) === value);
  const selectedLabel = selected ? contractOptionLabel(selected) : "";
  const [query, setQuery] = useState(selectedLabel);
  const lastSelectedLabel = useRef(selectedLabel);
  const listId = `${id}-options`;

  useEffect(() => {
    if (selectedLabel) {
      setQuery(selectedLabel);
      lastSelectedLabel.current = selectedLabel;
    } else if (!value && query === lastSelectedLabel.current) {
      setQuery("");
      lastSelectedLabel.current = "";
    }
  }, [query, selectedLabel, value]);

  function handleQueryChange(nextQuery: string) {
    setQuery(nextQuery);
    const exact = contratos.find((item) => contractOptionLabel(item) === nextQuery);
    onChange(exact ? String(exact.IDcontrato) : "");
  }

  return (
    <Field label={label} wide className="contract-field">
      <div className="contract-search">
        <Search size={17} />
        <input
          value={query}
          list={listId}
          onChange={(event) => handleQueryChange(event.target.value)}
          placeholder="Escribe codigo, nombre u obra"
          autoComplete="off"
          required
        />
      </div>
      <datalist id={listId}>
        {contratos.map((item) => (
          <option key={String(item.IDcontrato)} value={contractOptionLabel(item)} />
        ))}
      </datalist>
    </Field>
  );
}

function ChartCard({ title, detail, children }: { title: string; detail: string; children: ReactNode }) {
  return (
    <article className="chart-card">
      <header>
        <div>
          <span>Analisis</span>
          <h3>{title}</h3>
        </div>
        <p>{detail}</p>
      </header>
      {children}
    </article>
  );
}

function BarChart({ data, valueLabel = "registros" }: { data: ChartDatum[]; valueLabel?: string }) {
  const max = Math.max(...data.map((item) => item.value), 1);
  if (!data.length) return <div className="empty">No hay datos para graficar</div>;
  return (
    <div className="stat-bars">
      {data.map((item, index) => (
        <div className="stat-bar-row" key={item.label}>
          <span title={item.label}>{shortLabel(item.label, 24)}</span>
          <div>
            <i style={{ width: `${Math.max((item.value / max) * 100, 2)}%`, background: item.color ?? CHART_COLORS[index % CHART_COLORS.length] }} />
          </div>
          <strong>
            {valueLabel === "S/" ? `S/ ${formatValue(item.value)}` : `${formatValue(item.value)} ${valueLabel}`}
          </strong>
        </div>
      ))}
    </div>
  );
}

function PieChart({ data }: { data: ChartDatum[] }) {
  const total = data.reduce((sum, item) => sum + item.value, 0);
  const radius = 46;
  const circumference = 2 * Math.PI * radius;
  let offset = 0;

  if (!total) return <div className="empty">No hay datos para graficar</div>;

  return (
    <div className="pie-layout">
      <svg className="pie-chart" viewBox="0 0 120 120" role="img" aria-label="Grafico circular">
        <circle cx="60" cy="60" r={radius} fill="none" stroke="#edf1ea" strokeWidth="22" />
        {data.map((item, index) => {
          const length = (item.value / total) * circumference;
          const segment = (
            <circle
              key={item.label}
              cx="60"
              cy="60"
              r={radius}
              fill="none"
              stroke={item.color ?? CHART_COLORS[index % CHART_COLORS.length]}
              strokeDasharray={`${length} ${circumference - length}`}
              strokeDashoffset={-offset}
              strokeLinecap="butt"
              strokeWidth="22"
              transform="rotate(-90 60 60)"
            />
          );
          offset += length;
          return segment;
        })}
        <text x="60" y="57" textAnchor="middle" className="pie-chart__total">
          {formatValue(total)}
        </text>
        <text x="60" y="73" textAnchor="middle" className="pie-chart__label">
          total
        </text>
      </svg>
      <div className="pie-legend">
        {data.map((item, index) => (
          <span key={item.label}>
            <i style={{ background: item.color ?? CHART_COLORS[index % CHART_COLORS.length] }} />
            {item.label}
            <strong>{formatValue(item.value)}</strong>
          </span>
        ))}
      </div>
    </div>
  );
}

function LineChart({ data }: { data: ChartDatum[] }) {
  if (!data.length) return <div className="empty">No hay datos para graficar</div>;

  const width = 340;
  const height = 190;
  const paddingX = 34;
  const paddingY = 24;
  const max = Math.max(...data.map((item) => item.value), 1);
  const points = data.map((item, index) => {
    const x = data.length === 1 ? width / 2 : paddingX + (index * (width - paddingX * 2)) / (data.length - 1);
    const y = height - paddingY - (item.value / max) * (height - paddingY * 2);
    return { ...item, x, y };
  });

  return (
    <div className="line-chart-wrap">
      <svg className="line-chart" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Grafico de lineas">
        <line x1={paddingX} y1={height - paddingY} x2={width - paddingX} y2={height - paddingY} />
        <line x1={paddingX} y1={paddingY} x2={paddingX} y2={height - paddingY} />
        <polyline points={points.map((point) => `${point.x},${point.y}`).join(" ")} />
        {points.map((point) => (
          <g key={point.label}>
            <circle cx={point.x} cy={point.y} r="4" />
            <text x={point.x} y={height - 6} textAnchor="middle">
              {shortLabel(point.label, 7)}
            </text>
            <text x={point.x} y={Math.max(point.y - 9, 12)} textAnchor="middle" className="line-chart__value">
              {formatValue(point.value)}
            </text>
          </g>
        ))}
      </svg>
    </div>
  );
}

function GroupedDataTable({
  columns,
  rows,
  empty,
  collapsible = false,
  defaultOpen = true,
  scrollRows = false,
  searchable = false,
  searchPlaceholder = "Buscar"
}: {
  columns: Array<{ key: string; label: string; render?: (row: Row) => ReactNode }>;
  rows: Row[];
  empty: string;
  collapsible?: boolean;
  defaultOpen?: boolean;
  scrollRows?: boolean;
  searchable?: boolean;
  searchPlaceholder?: string;
}) {
  const [openGroups, setOpenGroups] = useState<Record<string, boolean>>({});
  const [groupSearch, setGroupSearch] = useState<Record<string, string>>({});
  if (!rows.length) return <div className="empty">{empty}</div>;

  return (
    <div className={collapsible ? "area-group-list area-group-list--collapsible" : "area-group-list"}>
      {groupRowsByArea(rows).map(([area, group], index) => {
        const isOpen = openGroups[area] ?? defaultOpen;
        const query = groupSearch[area]?.trim().toLowerCase() ?? "";
        const filteredGroup = searchable && query
          ? group.filter((row) => String(row.Empleado ?? row.Nombres ?? "").toLowerCase().includes(query))
          : group;
        const bodyId = `area-group-${area.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`;
        return (
          <section className={`area-group area-group--${index % 6} ${collapsible ? "area-group--collapsible" : ""} ${scrollRows ? "area-group--scroll" : ""}`} key={area}>
            {collapsible ? (
              <div className="area-group__title area-group__title--searchable">
                <button
                  className="area-group__toggle"
                  type="button"
                  aria-expanded={isOpen}
                  aria-controls={bodyId}
                  onClick={() => setOpenGroups((current) => ({ ...current, [area]: !isOpen }))}
                >
                  <span>{area.toUpperCase()}</span>
                  <small>
                    {group.length} registro{group.length === 1 ? "" : "s"}
                  </small>
                  <ChevronDown className="area-group__chevron" size={18} />
                </button>
                {searchable && (
                  <div className="area-group__search">
                    <Search size={16} />
                    <input
                      aria-label={`Buscar contratos de ${area}`}
                      placeholder={searchPlaceholder}
                      value={groupSearch[area] ?? ""}
                      onChange={(event) => {
                        const value = event.target.value;
                        setGroupSearch((current) => ({ ...current, [area]: value }));
                        if (!isOpen) setOpenGroups((current) => ({ ...current, [area]: true }));
                      }}
                    />
                  </div>
                )}
              </div>
            ) : (
              <div className="area-group__title">
                <span>{area.toUpperCase()}</span>
                <small>
                  {group.length} registro{group.length === 1 ? "" : "s"}
                </small>
              </div>
            )}
            {isOpen && (
              <div id={bodyId} className="area-group__body">
                <DataTable columns={columns} rows={filteredGroup} empty={query ? "No hay contratos con ese nombre" : empty} />
              </div>
            )}
          </section>
        );
      })}
    </div>
  );
}

function htmlValue(value: unknown) {
  return formatValue(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function downloadExcel(filename: string, rows: Row[]) {
  if (!rows.length) return;
  const headers = Object.keys(rows[0]);
  const table = [
    "<table>",
    `<thead><tr>${headers.map((header) => `<th>${htmlValue(header)}</th>`).join("")}</tr></thead>`,
    `<tbody>${rows
      .map((row) => `<tr>${headers.map((header) => `<td>${htmlValue(row[header])}</td>`).join("")}</tr>`)
      .join("")}</tbody>`,
    "</table>"
  ].join("");
  const html = `<!doctype html><html><head><meta charset="utf-8"></head><body>${table}</body></html>`;
  const blob = new Blob([html], { type: "application/vnd.ms-excel;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

function filenameFromDisposition(disposition: string | null, fallback: string) {
  if (!disposition) return fallback;
  const match = disposition.match(/filename="?([^"]+)"?/i);
  return match?.[1] ?? fallback;
}

async function downloadApiFile(path: string, fallbackFilename: string) {
  const token = localStorage.getItem("maaq_demo_token");
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {})
      }
    });
  } catch {
    throw new Error(`No se pudo conectar con el backend en ${API_URL}. Verifica que uvicorn este ejecutandose en el puerto 8000.`);
  }
  if (!response.ok) {
    const payload = await response.json().catch(() => ({ error: `Error HTTP ${response.status}` }));
    throw new Error(payload.error ?? `Error HTTP ${response.status}`);
  }
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filenameFromDisposition(response.headers.get("Content-Disposition"), fallbackFilename);
  link.click();
  URL.revokeObjectURL(url);
}

export function App() {
  const [authenticated, setAuthenticated] = useState(() => Boolean(localStorage.getItem("maaq_demo_token")));
  const [loginVisible, setLoginVisible] = useState(false);
  const [usuario, setUsuario] = useState<Row | null>(() => {
    const raw = localStorage.getItem("maaq_demo_user");
    return raw ? (JSON.parse(raw) as Row) : null;
  });
  const [loginForm, setLoginForm] = useState({ email: "admin@maaq.pe", password: "demo123" });
  const [active, setActive] = useState<ModuleId>("dashboard");
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [apiError, setApiError] = useState<string | null>(null);

  const [catalogs, setCatalogs] = useState<Catalogs>({});
  const [rrhhDashboard, setRrhhDashboard] = useState<RrhhDashboardData | null>(null);
  const [rrhhContratos, setRrhhContratos] = useState<Row[]>([]);
  const [rrhhAltas, setRrhhAltas] = useState<Row[]>([]);
  const [rrhhPlanilla, setRrhhPlanilla] = useState<Row[]>([]);
  const [rrhhReportes, setRrhhReportes] = useState<RrhhReportes>({ personal_activo: [], planilla_total: [], contratos_por_vencer: [] });
  const [rrhhAuditoria, setRrhhAuditoria] = useState<Row[]>([]);
  const [empleados, setEmpleados] = useState<Row[]>([]);
  const [obras, setObras] = useState<ObraOption[]>([]);
  const [busqueda, setBusqueda] = useState("");
  const [resultadosBusqueda, setResultadosBusqueda] = useState<Row[]>([]);
  const [documentoActual, setDocumentoActual] = useState<DocumentoGenerado | null>(null);
  const [reporteForm, setReporteForm] = useState(emptyReporte);
  const [reportePersonalizado, setReportePersonalizado] = useState<Row[]>([]);

  const [contratacionForm, setContratacionForm] = useState(emptyContratacion);
  const [renovacionForm, setRenovacionForm] = useState({ id_contrato: "", fecha_fin: addDays(60) });
  const [boletaForm, setBoletaForm] = useState(emptyBoleta);
  const [asistenciaForm, setAsistenciaForm] = useState(emptyAsistencia);
  const [destajoForm, setDestajoForm] = useState(emptyDestajo);
  const [editEmpleadoForm, setEditEmpleadoForm] = useState(emptyEditEmpleado);
  const [analisisVisible, setAnalisisVisible] = useState(false);
  const [contratosVista, setContratosVista] = useState<"contratos" | "fichas">("contratos");

  const activeModule = modules.find((item) => item.id === active);
  const activeMenu = moduleMenus[active];
  const contratoOptions = useMemo(() => rrhhContratos.filter((item) => String(item.Estado) !== "liquidado"), [rrhhContratos]);
  const asistenciaContrato = rrhhContratos.find((item) => String(item.IDcontrato) === asistenciaForm.id_contrato);
  const destajoContrato = rrhhContratos.find((item) => String(item.IDcontrato) === destajoForm.id_contrato);
  const obraSeleccionadaKey = contratacionForm.id_proyecto ? `proyecto:${contratacionForm.id_proyecto}` : contratacionForm.obra ? `obra:${contratacionForm.obra}` : "";
  const usaMesPago = reporteForm.tipo === "asistencia_mes_pago";
  const reportePersonalizadoColumns =
    reporteForm.tipo === "asistencia_mes_pago"
      ? [
          { key: "CodigoContrato", label: "Contrato" },
          { key: "Empleado", label: "Empleado" },
          { key: "NumeroDocumento", label: "Documento" },
          { key: "Obra", label: "Obra" },
          { key: "PeriodoPago", label: "Periodo" },
          { key: "DiasPeriodo", label: "Dias" },
          { key: "DiasRegistrados", label: "Reg." },
          { key: "Presentes", label: "Presentes" },
          { key: "Faltas", label: "Faltas" },
          { key: "Tardanzas", label: "Tardanzas" },
          { key: "Descansos", label: "Descansos" },
          { key: "Permisos", label: "Permisos" },
          { key: "Horas", label: "Horas" },
          { key: "Extras", label: "Extras" },
          { key: "FechasFalta", label: "Fechas falta" }
        ]
      : reporteForm.tipo === "planilla_rango"
      ? [
          { key: "Fecha", label: "Fecha" },
          { key: "Empleado", label: "Empleado" },
          { key: "NumeroDocumento", label: "Documento" },
          { key: "Obra", label: "Obra" },
          { key: "HorasLaboradas", label: "Horas" },
          { key: "Jornal", label: "Jornal" },
          { key: "Extras", label: "Extras" },
          { key: "TotalDestajo", label: "Destajo" },
          { key: "TotalPlanilla", label: "Total" }
        ]
      : [
          { key: "CodigoContrato", label: "Contrato" },
          { key: "Empleado", label: "Empleado" },
          { key: "NumeroDocumento", label: "Documento" },
          { key: "Obra", label: "Obra" },
          { key: "Cargo", label: "Cargo" },
          { key: "FechaInicio", label: "Ingreso" },
          { key: "FechaFin", label: "Fin" },
          { key: "DiasRestantes", label: "Dias" },
          { key: "Estado", label: "Estado" },
          { key: "Semaforo", label: "Semaforo", render: (row: Row) => <SemaforoBadge value={row.Semaforo} /> }
        ];
  const reporteTitulo = reporteTipos.find((item) => item.value === reporteForm.tipo)?.label ?? "Reporte personalizado";
  const reporteResumen = useMemo(() => {
    const grouped = groupRowsByArea(reportePersonalizado);
    const semaforo = { rojo: 0, amarillo: 0, verde: 0 };
    const estados: Record<string, number> = {};
    let totalPlanilla = 0;
    let totalDestajo = 0;
    let totalHoras = 0;
    let totalFaltas = 0;
    let totalTardanzas = 0;
    let totalSinRegistro = 0;
    const areas = grouped.map(([area, rows]) => {
      const areaData = { area, registros: rows.length, rojo: 0, amarillo: 0, verde: 0, totalPlanilla: 0, faltas: 0, tardanzas: 0, sinRegistro: 0 };
      rows.forEach((row) => {
        const sem = String(row.Semaforo ?? "").toLowerCase();
        if (sem === "rojo" || sem === "amarillo" || sem === "verde") {
          semaforo[sem] += 1;
          areaData[sem] += 1;
        }
        const estado = String(row.Estado ?? "sin dato").toLowerCase();
        estados[estado] = (estados[estado] ?? 0) + 1;
        const planilla = Number(row.TotalPlanilla ?? 0);
        const destajo = Number(row.TotalDestajo ?? 0);
        const horas = Number(row.HorasLaboradas ?? row.Horas ?? 0);
        const faltas = Number(row.Faltas ?? 0);
        const tardanzas = Number(row.Tardanzas ?? 0);
        const sinRegistro = Number(row.DiasSinRegistro ?? 0);
        totalPlanilla += Number.isFinite(planilla) ? planilla : 0;
        totalDestajo += Number.isFinite(destajo) ? destajo : 0;
        totalHoras += Number.isFinite(horas) ? horas : 0;
        totalFaltas += Number.isFinite(faltas) ? faltas : 0;
        totalTardanzas += Number.isFinite(tardanzas) ? tardanzas : 0;
        totalSinRegistro += Number.isFinite(sinRegistro) ? sinRegistro : 0;
        areaData.totalPlanilla += Number.isFinite(planilla) ? planilla : 0;
        areaData.faltas += Number.isFinite(faltas) ? faltas : 0;
        areaData.tardanzas += Number.isFinite(tardanzas) ? tardanzas : 0;
        areaData.sinRegistro += Number.isFinite(sinRegistro) ? sinRegistro : 0;
      });
      return areaData;
    });
    return {
      areas,
      estados,
      semaforo,
      totalPlanilla,
      totalDestajo,
      totalHoras,
      totalFaltas,
      totalTardanzas,
      totalSinRegistro
    };
  }, [reportePersonalizado]);
  const reporteKpis =
    reporteForm.tipo === "asistencia_mes_pago"
      ? [
          { label: "Contratos", value: formatValue(reportePersonalizado.length), tone: "rose" },
          { label: "Areas", value: formatValue(reporteResumen.areas.length), tone: "teal" },
          { label: "Faltas", value: formatValue(reporteResumen.totalFaltas), tone: "red" },
          { label: "Tardanzas", value: formatValue(reporteResumen.totalTardanzas), tone: "amber" },
          { label: "Horas", value: formatValue(Number(reporteResumen.totalHoras.toFixed(2))), tone: "blue" },
          { label: "Sin registro", value: formatValue(reporteResumen.totalSinRegistro), tone: "green" }
        ]
      : reporteForm.tipo === "planilla_rango"
      ? [
          { label: "Registros", value: formatValue(reportePersonalizado.length), tone: "rose" },
          { label: "Areas", value: formatValue(reporteResumen.areas.length), tone: "teal" },
          { label: "Horas", value: formatValue(Number(reporteResumen.totalHoras.toFixed(2))), tone: "amber" },
          { label: "Planilla", value: formatMoney(reporteResumen.totalPlanilla), tone: "blue" }
        ]
      : [
          { label: "Registros", value: formatValue(reportePersonalizado.length), tone: "rose" },
          { label: "Areas", value: formatValue(reporteResumen.areas.length), tone: "teal" },
          { label: "Rojo", value: formatValue(reporteResumen.semaforo.rojo), tone: "red" },
          { label: "Amarillo", value: formatValue(reporteResumen.semaforo.amarillo), tone: "amber" },
          { label: "Verde", value: formatValue(reporteResumen.semaforo.verde), tone: "green" },
          { label: "Activos", value: formatValue(reporteResumen.estados.activo ?? 0), tone: "blue" }
        ];
  const analisisEstadistico = useMemo(() => {
    const contratosActivos = rrhhContratos.filter((row) => String(row.Estado ?? "").toLowerCase() !== "liquidado");
    const contratosPorArea = groupRowsByArea(contratosActivos).map(([area, rows], index) => ({
      label: area,
      value: rows.length,
      color: CHART_COLORS[index % CHART_COLORS.length]
    }));

    const obrasMap = new Map<string, number>();
    const costoAreaMap = new Map<string, number>();
    const altasMesMap = new Map<string, number>();
    const bajasMesMap = new Map<string, number>();
    const semaforoMap = new Map<string, number>();

    rrhhContratos.forEach((row) => {
      const fechaBaja = String(row.FechaLiquidacion ?? "");
      const mesBaja = fechaBaja.slice(0, 7);
      if (/^\d{4}-\d{2}$/.test(mesBaja)) {
        bajasMesMap.set(mesBaja, (bajasMesMap.get(mesBaja) ?? 0) + 1);
      }
    });

    contratosActivos.forEach((row) => {
      const obra = String(row.Obra ?? "Sin obra");
      const area = areaLabel(row);
      const semaforo = String(row.Semaforo ?? "sin dato").toLowerCase();
      const fechaInicio = String(row.FechaInicio ?? "");
      const mes = fechaInicio.slice(0, 7);
      const costoMensual = numericValue(row.SalarioDiario) * 30;

      obrasMap.set(obra, (obrasMap.get(obra) ?? 0) + 1);
      costoAreaMap.set(area, (costoAreaMap.get(area) ?? 0) + costoMensual);
      semaforoMap.set(semaforo, (semaforoMap.get(semaforo) ?? 0) + 1);
      if (/^\d{4}-\d{2}$/.test(mes)) {
        altasMesMap.set(mes, (altasMesMap.get(mes) ?? 0) + 1);
      }
    });

    const contratosPorObra = Array.from(obrasMap.entries())
      .map(([label, value], index) => ({ label, value, color: CHART_COLORS[index % CHART_COLORS.length] }))
      .sort((a, b) => b.value - a.value)
      .slice(0, 8);
    const costoMensualPorArea = Array.from(costoAreaMap.entries())
      .map(([label, value], index) => ({ label, value: Math.round(value), color: CHART_COLORS[index % CHART_COLORS.length] }))
      .sort((a, b) => b.value - a.value);
    const altasPorMes = Array.from(altasMesMap.entries())
      .sort(([mesA], [mesB]) => mesA.localeCompare(mesB))
      .slice(-10)
      .map(([label, value]) => ({ label, value, color: "#ff3f62" }));
    const bajasPorMes = Array.from(bajasMesMap.entries())
      .sort(([mesA], [mesB]) => mesA.localeCompare(mesB))
      .slice(-10)
      .map(([label, value]) => ({ label, value, color: "#2563eb" }));
    const semaforoContratos = ["rojo", "amarillo", "verde", "gris"]
      .map((label, index) => ({
        label,
        value: semaforoMap.get(label) ?? 0,
        color: ["#be123c", "#f59e0b", "#0f766e", "#6b7280"][index]
      }))
      .filter((item) => item.value > 0);

    return {
      contratosActivos,
      contratosPorArea,
      contratosPorObra,
      costoMensualPorArea,
      altasPorMes,
      bajasPorMes,
      semaforoContratos,
      totalCostoMensual: costoMensualPorArea.reduce((sum, item) => sum + item.value, 0),
      totalObras: obrasMap.size,
      totalAreas: contratosPorArea.length,
      personalActivo: new Set(contratosActivos.map((row) => row.IDempleado)).size
    };
  }, [rrhhContratos]);

  async function refreshAll() {
    if (!authenticated) return;
    setLoading(true);
    setNotice(null);
    try {
      const [catalogData, dashboardData, contratosData, altasData, planillaData, reportesData, auditoriaData, empleadosData, obrasData] = await Promise.all([
        api<Catalogs>("/catalogos"),
        api<RrhhDashboardData>("/rrhh/dashboard"),
        api<Row[]>("/rrhh/contratos"),
        api<Row[]>("/rrhh/altas"),
        api<Row[]>("/rrhh/planilla"),
        api<RrhhReportes>("/rrhh/reportes/globales"),
        api<Row[]>("/rrhh/auditoria"),
        api<Row[]>("/empleados"),
        api<ObraOption[]>("/rrhh/obras")
      ]);
      setCatalogs(catalogData);
      setRrhhDashboard(dashboardData);
      setRrhhContratos(contratosData);
      setRrhhAltas(altasData);
      setRrhhPlanilla(planillaData);
      setRrhhReportes(reportesData);
      setRrhhAuditoria(auditoriaData);
      setEmpleados(empleadosData);
      setObras(obrasData);
      setApiError(null);
    } catch (error) {
      setApiError(error instanceof Error ? error.message : "No se pudo conectar con la API");
    } finally {
      setLoading(false);
    }
  }

  async function submit(label: string, action: () => Promise<void>) {
    setSaving(label);
    setNotice(null);
    setApiError(null);
    try {
      await action();
      setNotice("Operacion registrada");
      await refreshAll();
    } catch (error) {
      setApiError(error instanceof Error ? error.message : "No se pudo completar la operacion");
    } finally {
      setSaving(null);
    }
  }

  useEffect(() => {
    api<{ email: string; password: string }>("/auth/demo")
      .then((data) => setLoginForm(data))
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    if (authenticated) refreshAll();
  }, [authenticated]);

  async function saveLogin(event: FormEvent) {
    event.preventDefault();
    setSaving("login");
    setApiError(null);
    try {
      const data = await api<LoginResponse>("/auth/login", {
        method: "POST",
        body: JSON.stringify(loginForm)
      });
      localStorage.setItem("maaq_demo_token", data.token);
      localStorage.setItem("maaq_demo_user", JSON.stringify(data.usuario));
      setUsuario(data.usuario);
      setAuthenticated(true);
      setActive("dashboard");
      window.scrollTo(0, 0);
    } catch (error) {
      setApiError(error instanceof Error ? error.message : "No se pudo iniciar sesion");
    } finally {
      setSaving(null);
    }
  }

  function logout() {
    localStorage.removeItem("maaq_demo_token");
    localStorage.removeItem("maaq_demo_user");
    setAuthenticated(false);
    setLoginVisible(false);
    setUsuario(null);
    setActive("dashboard");
    window.scrollTo(0, 0);
  }

  function updateContratacion(key: keyof typeof contratacionForm, value: string) {
    setContratacionForm((current) => {
      if (key === "area") {
        return { ...current, area: value, salario_diario: salarioDiarioArea(value) };
      }
      return { ...current, [key]: value };
    });
  }

  function selectObraContratacion(value: string) {
    const selected = obras.find((item) => obraOptionKey(item) === value);
    setContratacionForm((current) => ({
      ...current,
      id_proyecto: selected?.IDproyecto ? String(selected.IDproyecto) : "",
      obra: selected?.NombreObra ?? ""
    }));
  }

  function updateAsistencia(key: keyof typeof asistenciaForm, value: string) {
    setAsistenciaForm((current) => ({ ...current, [key]: value }));
  }

  function updateDestajo(key: keyof typeof destajoForm, value: string) {
    setDestajoForm((current) => ({ ...current, [key]: value }));
  }

  function updateReporte(key: keyof typeof reporteForm, value: string) {
    setReporteForm((current) => ({ ...current, [key]: value }));
  }

  function selectContrato(idContrato: string, target: "asistencia" | "destajo") {
    const contrato = rrhhContratos.find((item) => String(item.IDcontrato) === idContrato);
    const next = {
      id_contrato: idContrato,
      id_empleado: String(contrato?.IDempleado ?? ""),
      obra: String(contrato?.Obra ?? "")
    };
    if (target === "asistencia") {
      setAsistenciaForm((current) => ({ ...current, ...next }));
    } else {
      setDestajoForm((current) => ({ ...current, ...next }));
    }
  }

  async function saveContratacion(event: FormEvent) {
    event.preventDefault();
    const confirmar = window.confirm(
      `Confirma la contratacion de ${contratacionForm.nombres} ${contratacionForm.apellido_paterno} para la obra ${contratacionForm.obra}?`
    );
    if (!confirmar) return;
    await submit("contratacion", async () => {
      await api("/rrhh/contratacion", {
        method: "POST",
        body: JSON.stringify({
          id_tipo_documento: asNumber(contratacionForm.id_tipo_documento),
          numero_documento: contratacionForm.numero_documento,
          apellido_paterno: contratacionForm.apellido_paterno,
          apellido_materno: contratacionForm.apellido_materno,
          nombres: contratacionForm.nombres,
          email: contratacionForm.email,
          celular: contratacionForm.celular,
          id_tipo_empleado: optionalNumber(contratacionForm.id_tipo_empleado),
          area: optionalText(contratacionForm.area),
          id_proyecto: optionalNumber(contratacionForm.id_proyecto),
          obra: contratacionForm.obra,
          cargo: contratacionForm.cargo,
          fecha_inicio: contratacionForm.fecha_inicio,
          fecha_fin: contratacionForm.fecha_fin,
          salario_diario: Number(contratacionForm.salario_diario)
        })
      });
      setContratacionForm({ ...emptyContratacion, id_tipo_documento: contratacionForm.id_tipo_documento });
    });
  }

  async function saveRenovacion(event: FormEvent) {
    event.preventDefault();
    if (!renovacionForm.id_contrato) {
      setApiError("Selecciona un contrato para renovar");
      return;
    }
    await submit("renovacion", async () => {
      await api(`/rrhh/contratos/${renovacionForm.id_contrato}/renovar`, {
        method: "POST",
        body: JSON.stringify({ fecha_fin: renovacionForm.fecha_fin })
      });
      setRenovacionForm({ id_contrato: "", fecha_fin: addDays(60) });
    });
  }

  async function liquidarContrato(idContrato: unknown) {
    if (!idContrato) return;
    const contrato = rrhhContratos.find((item) => String(item.IDcontrato) === String(idContrato));
    const confirmar = window.confirm(
      `Confirma liquidar el contrato ${formatValue(contrato?.CodigoContrato ?? idContrato)} de ${formatValue(contrato?.Empleado)}? Esta accion cambiara el estado del contrato.`
    );
    if (!confirmar) return;
    await submit("liquidacion", async () => {
      await api(`/rrhh/contratos/${idContrato}/liquidar`, { method: "POST" });
    });
  }

  async function abrirDocumento(path: string) {
    setSaving("documento");
    setNotice(null);
    setApiError(null);
    try {
      const documento = await api<DocumentoGenerado>(path);
      setDocumentoActual(documento);
      setNotice(`Documento listo para exportar: ${documento.filename}`);
      await refreshAll();
    } catch (error) {
      setApiError(error instanceof Error ? error.message : "No se pudo generar el documento");
    } finally {
      setSaving(null);
    }
  }

  async function descargarPdf(path: string, fallback: string) {
    setSaving("pdf");
    setNotice(null);
    setApiError(null);
    try {
      const token = localStorage.getItem("maaq_demo_token");
      const response = await fetch(`${API_URL}${path}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : undefined
      });
      if (!response.ok) {
        const payload = await response.json().catch(() => null);
        throw new Error(payload?.error ?? `No se pudo descargar el PDF (${response.status})`);
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filenameFromDisposition(response.headers.get("Content-Disposition"), fallback);
      link.click();
      URL.revokeObjectURL(url);
      setNotice("PDF descargado");
    } catch (error) {
      setApiError(error instanceof Error ? error.message : "No se pudo descargar el PDF");
    } finally {
      setSaving(null);
    }
  }

  function pdfPathDocumento(documento: DocumentoGenerado | null) {
    const contrato = documento?.data?.contrato as Row | undefined;
    const idContrato = contrato?.IDcontrato;
    if (!idContrato) return null;
    if (documento?.tipo === "contrato") {
      return `/rrhh/contratos/${idContrato}/documentos/contrato/pdf`;
    }
    if (documento?.tipo === "certificado") {
      return `/rrhh/contratos/${idContrato}/documentos/certificado/pdf`;
    }
    return null;
  }

  function imprimirDocumento() {
    const iframe = document.getElementById("documento-preview") as HTMLIFrameElement | null;
    iframe?.contentWindow?.focus();
    iframe?.contentWindow?.print();
  }

  function descargarDocumentoHtml() {
    if (!documentoActual) return;
    const blob = new Blob([documentoActual.html], { type: "text/html;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = documentoActual.filename;
    link.click();
    URL.revokeObjectURL(url);
  }

  async function saveBoleta(event: FormEvent) {
    event.preventDefault();
    if (!boletaForm.id_contrato) {
      setApiError("Selecciona un contrato para generar la boleta");
      return;
    }
    await abrirDocumento(
      `/rrhh/contratos/${boletaForm.id_contrato}/documentos/boleta?fecha_cese=${encodeURIComponent(boletaForm.fecha_cese)}&motivo=${encodeURIComponent(boletaForm.motivo)}`
    );
  }

  async function saveAsistencia(event: FormEvent) {
    event.preventDefault();
    if (!asistenciaForm.id_contrato) {
      setApiError("Selecciona un contrato valido para registrar asistencia");
      return;
    }
    await submit("asistencia", async () => {
      await api("/rrhh/asistencia", {
        method: "POST",
        body: JSON.stringify({
          id_empleado: asNumber(asistenciaForm.id_empleado),
          id_contrato: optionalNumber(asistenciaForm.id_contrato),
          fecha: asistenciaForm.fecha,
          obra: asistenciaForm.obra,
          estado: asistenciaForm.estado,
          horas: Number(asistenciaForm.horas),
          extras: Number(asistenciaForm.extras),
          observacion: optionalText(asistenciaForm.observacion)
        })
      });
      setAsistenciaForm(emptyAsistencia);
    });
  }

  async function saveDestajo(event: FormEvent) {
    event.preventDefault();
    if (!destajoForm.id_contrato) {
      setApiError("Selecciona un contrato valido para registrar destajo");
      return;
    }
    await submit("destajo", async () => {
      await api("/rrhh/destajo", {
        method: "POST",
        body: JSON.stringify({
          id_empleado: asNumber(destajoForm.id_empleado),
          id_contrato: optionalNumber(destajoForm.id_contrato),
          fecha: destajoForm.fecha,
          obra: destajoForm.obra,
          partida: destajoForm.partida,
          metrado: Number(destajoForm.metrado),
          tarifa: Number(destajoForm.tarifa),
          observacion: optionalText(destajoForm.observacion)
        })
      });
      setDestajoForm(emptyDestajo);
    });
  }

  async function buscarEmpleado(event: FormEvent) {
    event.preventDefault();
    if (!busqueda.trim()) return;
    await submit("busqueda", async () => {
      const data = await api<Row[]>(`/rrhh/buscar?q=${encodeURIComponent(busqueda.trim())}`);
      setResultadosBusqueda(data);
    });
  }

  function reporteParams() {
    const params = new URLSearchParams();
    params.set("tipo", reporteForm.tipo);
    if (reporteForm.area) params.set("area", reporteForm.area);
    if (reporteForm.estado) params.set("estado", reporteForm.estado);
    if (reporteForm.desde) params.set("desde", reporteForm.desde);
    if (reporteForm.hasta) params.set("hasta", reporteForm.hasta);
    if (reporteForm.mes_pago) params.set("mes_pago", reporteForm.mes_pago);
    if (reporteForm.q.trim()) params.set("q", reporteForm.q.trim());
    if (reporteForm.dias) params.set("dias", reporteForm.dias);
    if (reporteForm.limit) params.set("limit", reporteForm.limit);
    return params;
  }

  async function generarReporte(event: FormEvent) {
    event.preventDefault();
    setSaving("reporte-personalizado");
    setNotice(null);
    setApiError(null);
    try {
      const data = await api<Row[]>(`/rrhh/reportes/personalizado?${reporteParams().toString()}`);
      setReportePersonalizado(data);
      setNotice(`Reporte generado: ${countLabel(data.length)}`);
    } catch (error) {
      setApiError(error instanceof Error ? error.message : "No se pudo generar el reporte");
    } finally {
      setSaving(null);
    }
  }

  async function descargarReportePersonalizado(formato: "excel" | "pdf") {
    const params = reporteParams();
    params.set("formato", formato);
    setSaving(`reporte-${formato}`);
    setNotice(null);
    setApiError(null);
    try {
      await downloadApiFile(
        `/rrhh/reportes/personalizado/export?${params.toString()}`,
        formato === "excel" ? "reporte-personalizado-maaq.xlsx" : "reporte-personalizado-maaq.pdf"
      );
      setNotice(`Reporte descargado en ${formato === "excel" ? "Excel" : "PDF"}`);
    } catch (error) {
      setApiError(error instanceof Error ? error.message : "No se pudo descargar el reporte");
    } finally {
      setSaving(null);
    }
  }

  function cargarEdicion(row: Row) {
    setEditEmpleadoForm({
      id_empleado: String(row.IDempleado ?? ""),
      numero_documento: String(row.NumeroDocumento ?? ""),
      nombres: String(row.Nombres ?? ""),
      apellido_paterno: String(row.ApellidoPaterno ?? ""),
      apellido_materno: String(row.ApellidoMaterno ?? ""),
      email: String(row.Email ?? ""),
      celular: String(row.Celular ?? ""),
      area: areaLabel(row)
    });
  }

  async function saveEditEmpleado(event: FormEvent) {
    event.preventDefault();
    if (!editEmpleadoForm.id_empleado) {
      setApiError("Selecciona un empleado desde la busqueda");
      return;
    }
    await submit("editar-empleado", async () => {
      await api(`/empleados/${editEmpleadoForm.id_empleado}`, {
        method: "PATCH",
        body: JSON.stringify({
          nombres: editEmpleadoForm.nombres,
          apellido_paterno: editEmpleadoForm.apellido_paterno,
          apellido_materno: editEmpleadoForm.apellido_materno,
          email: editEmpleadoForm.email,
          celular: editEmpleadoForm.celular,
          usuario: "admin-demo"
        })
      });
      await api(`/rrhh/empleados/${editEmpleadoForm.id_empleado}/area`, {
        method: "PATCH",
        body: JSON.stringify({ area: editEmpleadoForm.area })
      });
      setEditEmpleadoForm(emptyEditEmpleado);
    });
  }

  const documentoPdfPath = pdfPathDocumento(documentoActual);

  if (!authenticated) {
    return (
      <main className="login-page" id="inicio">
        <section className={loginVisible ? "login-panel" : "login-panel login-panel--home"}>
          <div className="login-showcase">
            <div className="login-topline">
              <div className="brand brand--login">
                <span className="brand__mark">MQ</span>
                <div>
                  <strong>TPS MAAQ</strong>
                  <small>Constructora MAAQ S.A.C.</small>
                </div>
              </div>
              <nav className="public-nav-links" aria-label="Navegacion publica">
                <a href="#inicio">Inicio</a>
                <a href="#empresa">Empresa</a>
                <a href="#mision">Mision</a>
                <a href="#vision">Vision</a>
              </nav>
              {!loginVisible && (
                <button className="primary login-top-button" onClick={() => setLoginVisible(true)}>
                  <LogIn size={18} />
                  Iniciar sesion
                </button>
              )}
            </div>

            <div className="login-hero-copy">
              <p className="eyebrow">Portal RRHH para obra</p>
              <h1>Contrata, controla contratos y calcula planillas desde un TPS conectado a SQL Server.</h1>
              <p>
                Plataforma demo orientada a Constructora MAAQ S.A.C. para manejar personal, alertas de contrato,
                asistencia diaria y destajo por obra.
              </p>
            </div>

            <div className="login-feature-grid" id="empresa">
              <article>
                <UserRoundPlus size={20} />
                <span>Modulo 1</span>
                <strong>Contratacion e incorporacion de personal</strong>
              </article>
              <article>
                <CalendarClock size={20} />
                <span>Modulo 2</span>
                <strong>Control de contratos con alertas de vigencia</strong>
              </article>
              <article>
                <WalletCards size={20} />
                <span>Modulo 3</span>
                <strong>Asistencia, destajo y costo de mano de obra</strong>
              </article>
            </div>

            <div className="login-purpose-strip">
              {companyPurpose.map((item) => (
                <article key={item.title} id={item.title === "Mision" ? "mision" : "vision"}>
                  <span>{item.title}</span>
                  <p>{item.body}</p>
                </article>
              ))}
            </div>
          </div>

          {loginVisible && (
            <aside className="login-access">
              <div className="login-access__top">
                <span className="login-badge">
                  <ShieldCheck size={16} />
                  Demo segura
                </span>
                <button className="login-link-button" onClick={() => setLoginVisible(false)} type="button">
                  Volver al inicio
                </button>
              </div>
              <form className="login-card" onSubmit={saveLogin}>
                <div>
                  <p className="eyebrow">Credenciales precargadas</p>
                  <h2>Ingreso al sistema</h2>
                  <p className="login-muted">Accede al panel RRHH conectado a la base `maaq_db`.</p>
                </div>
                {apiError && <div className="alert">{apiError}</div>}
                <Field label="Gmail">
                  <input value={loginForm.email} onChange={(event) => setLoginForm({ ...loginForm, email: event.target.value })} type="email" autoComplete="username" required />
                </Field>
                <Field label="Contrasena">
                  <input value={loginForm.password} onChange={(event) => setLoginForm({ ...loginForm, password: event.target.value })} type="password" autoComplete="current-password" required />
                </Field>
                <button className="primary login-submit" disabled={saving === "login"}>
                  <LogIn size={18} />
                  Ingresar demo
                </button>
              </form>
              <div className="login-checklist">
                {bpmFocus.map((item) => (
                  <span key={item}>
                    <CheckCircle2 size={15} />
                    {item}
                  </span>
                ))}
              </div>
            </aside>
          )}
        </section>
        <footer className="public-footer">
          <div>
            <strong>TPS MAAQ</strong>
            <span>Gestion RRHH para Constructora MAAQ S.A.C.</span>
          </div>
          <span className="public-footer__meta">Tingo Maria, Peru</span>
        </footer>
      </main>
    );
  }

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand__mark">MQ</span>
          <div>
            <strong>TPS MAAQ</strong>
            <small>Gestion RRHH</small>
          </div>
        </div>

        <nav className="nav">
          {modules.map((item) => (
            <button
              key={item.id}
              className={active === item.id ? "nav__item nav__item--active" : "nav__item"}
              onClick={() => setActive(item.id)}
              title={item.label}
            >
              {item.icon}
              <span>{item.label}</span>
            </button>
          ))}
        </nav>
        <div className="nav-actions">
          <button className="nav-action-button" onClick={refreshAll} disabled={loading} title="Actualizar datos">
            <RefreshCw size={18} />
          </button>
          <button className="nav-action-button" onClick={logout} title="Cerrar sesion">
            <LogOut size={18} />
          </button>
        </div>
      </aside>

      <main className="main">
        <header className="topbar">
          <div>
            <h1>{activeModule?.label}</h1>
          </div>
        </header>

        <div className="workspace">
          <aside className="module-sidebar">
            <p className="eyebrow">Modulo activo</p>
            <h2>{activeModule?.label}</h2>
            <div className="module-menu">
              {activeMenu.map((item, index) => (
                <button type="button" key={item.label} className={index === 0 ? "module-menu__item module-menu__item--active" : "module-menu__item"}>
                  <span>{String(index + 1).padStart(2, "0")}</span>
                  <strong>{item.label}</strong>
                  <small>{item.detail}</small>
                </button>
              ))}
            </div>
          </aside>

          <div className="workspace-body">
            {apiError && <div className="alert">{apiError}</div>}
            {notice && <div className="notice">{notice}</div>}

            {active === "dashboard" && (
              <section className="section-grid">
                <section className="company-hero">
                  <div className="company-hero__copy">
                    <p className="eyebrow">Constructora MAAQ S.A.C.</p>
                    <h2>Dashboard principal de personal, contratos y planilla</h2>
                    <p>
                      El flujo RRHH se divide en contratacion e incorporacion, control del ciclo de vida de contratos,
                      y asistencia con destajo por obra.
                    </p>
                  </div>
                  <div className="fact-grid">
                    {companyFacts.map((fact) => (
                      <article className="fact" key={fact.label}>
                        <span>{fact.label}</span>
                        <strong>{fact.value}</strong>
                      </article>
                    ))}
                  </div>
                </section>

                <div className="kpi-grid">
                  {Object.entries(rrhhDashboard?.kpis ?? {}).map(([key, value]) => (
                    <article className="kpi" key={key}>
                      <span>{key.replace(/_/g, " ")}</span>
                      <strong>{formatValue(value)}</strong>
                    </article>
                  ))}
                </div>

                <section className="surface workflow-surface">
                  <div className="surface-head">
                    <h2>Flujo de trabajo RRHH</h2>
                    <button className="ghost" onClick={() => setActive("reportes")}>
                      <FileText size={16} />
                      Reportes globales
                    </button>
                  </div>
                  <div className="workflow-map">
                    <div className="workflow-row workflow-row--center">
                      <span className="workflow-pill workflow-pill--admin">Login admin</span>
                      <span className="workflow-pill workflow-pill--dash">Dashboard principal</span>
                    </div>
                    <div className="workflow-grid">
                      <article className="workflow-card workflow-card--hire">
                        <button type="button" onClick={() => setActive("contratacion")}>M1 Contratacion</button>
                        <span>Nuevo empleado</span>
                        <span>Validacion automatica</span>
                        <span>Empleado guardado + contrato</span>
                        <button type="button" className="workflow-report" onClick={() => setActive("contratacion")}>Reporte de altas</button>
                      </article>
                      <article className="workflow-card workflow-card--contract">
                        <button type="button" onClick={() => setActive("contratos")}>M2 Control de contratos</button>
                        <span>Lista semaforo</span>
                        <span>Renovar o liquidar</span>
                        <span>Calculo de liquidacion</span>
                        <button type="button" className="workflow-report" onClick={() => setActive("contratos")}>Vigencia y bajas</button>
                      </article>
                      <article className="workflow-card workflow-card--attendance">
                        <button type="button" onClick={() => setActive("asistencia")}>M3 Asistencia y destajo</button>
                        <span>Registrar asistencia</span>
                        <span>Ingresar destajo</span>
                        <span>Generar planilla</span>
                        <button type="button" className="workflow-report" onClick={() => setActive("asistencia")}>Boletas + costo MO</button>
                      </article>
                    </div>
                  </div>
                </section>

                <div className="split">
                  <section className="surface">
                    <h2>Semaforo de contratos</h2>
                    <DataTable
                      columns={[
                        { key: "Semaforo", label: "Semaforo", render: (row) => <SemaforoBadge value={row.Semaforo} /> },
                        { key: "total", label: "Total" }
                      ]}
                      rows={rrhhDashboard?.semaforo ?? []}
                      empty="No hay contratos registrados"
                    />
                  </section>
                  <section className="surface">
                    <h2>Ultimos contratos</h2>
                    <GroupedDataTable
                      columns={[
                        { key: "CodigoContrato", label: "Contrato" },
                        { key: "Empleado", label: "Empleado" },
                        { key: "Obra", label: "Obra" },
                        { key: "Semaforo", label: "Estado", render: (row) => <SemaforoBadge value={row.Semaforo} /> }
                      ]}
                      rows={rrhhDashboard?.ultimos_contratos ?? []}
                      empty="No hay contratos registrados"
                    />
                  </section>
                </div>
              </section>
            )}

            {active === "contratacion" && (
              <section className="section-grid">
                <form className="surface form-grid" onSubmit={saveContratacion}>
                  <div className="form-title">
                    <h2>Nuevo empleado + contrato</h2>
                  </div>
                  <CatalogField label="Documento" value={contratacionForm.id_tipo_documento} onChange={(v) => updateContratacion("id_tipo_documento", v)} items={catalogs["tipo-documento"]} />
                  <Field label="DNI / documento">
                    <input value={contratacionForm.numero_documento} onChange={(e) => updateContratacion("numero_documento", e.target.value)} required maxLength={15} />
                  </Field>
                  <Field label="Nombres">
                    <input value={contratacionForm.nombres} onChange={(e) => updateContratacion("nombres", e.target.value)} required maxLength={50} />
                  </Field>
                  <Field label="Apellido paterno">
                    <input value={contratacionForm.apellido_paterno} onChange={(e) => updateContratacion("apellido_paterno", e.target.value)} required maxLength={50} />
                  </Field>
                  <Field label="Apellido materno">
                    <input value={contratacionForm.apellido_materno} onChange={(e) => updateContratacion("apellido_materno", e.target.value)} required maxLength={50} />
                  </Field>
                  <Field label="Email">
                    <input value={contratacionForm.email} onChange={(e) => updateContratacion("email", e.target.value)} type="email" required maxLength={100} />
                  </Field>
                  <Field label="Celular">
                    <input value={contratacionForm.celular} onChange={(e) => updateContratacion("celular", e.target.value)} required maxLength={20} />
                  </Field>
                  <CatalogField label="Tipo empleado" value={contratacionForm.id_tipo_empleado} onChange={(v) => updateContratacion("id_tipo_empleado", v)} items={catalogs["tipo-empleado"]} required={false} />
                  <Field label="Area">
                    <select value={contratacionForm.area} onChange={(e) => updateContratacion("area", e.target.value)} required>
                      <option value="">Seleccionar area</option>
                      {AREA_OPTIONS.map((area) => (
                        <option key={area} value={area}>
                          {area}
                        </option>
                      ))}
                    </select>
                  </Field>
                  <Field label="Obra">
                    <select value={obraSeleccionadaKey} onChange={(e) => selectObraContratacion(e.target.value)} required>
                      <option value="">Seleccionar obra</option>
                      {obras.map((obra) => (
                        <option key={obraOptionKey(obra)} value={obraOptionKey(obra)}>
                          {obra.label}
                        </option>
                      ))}
                    </select>
                  </Field>
                  <Field label="Cargo">
                    <input value={contratacionForm.cargo} onChange={(e) => updateContratacion("cargo", e.target.value)} required maxLength={80} />
                  </Field>
                  <Field label="Inicio">
                    <input value={contratacionForm.fecha_inicio} onChange={(e) => updateContratacion("fecha_inicio", e.target.value)} type="date" required />
                  </Field>
                  <Field label="Fin contrato">
                    <input value={contratacionForm.fecha_fin} onChange={(e) => updateContratacion("fecha_fin", e.target.value)} type="date" required />
                  </Field>
                  <Field label="Sueldo mensual simulado">
                    <input value={formatMoney(salarioMensualArea(contratacionForm.area))} readOnly />
                  </Field>
                  <Field label="Jornal diario">
                    <input value={contratacionForm.salario_diario} type="number" min="0" step="0.01" readOnly required />
                  </Field>
                  <div className="form-actions">
                    <button className="primary" disabled={saving === "contratacion"}>
                      <Save size={17} />
                      Guardar empleado
                    </button>
                  </div>
                </form>
                <section className="surface">
                  <h2>Reporte de altas</h2>
                  <GroupedDataTable
                    columns={[
                      { key: "IDcontrato", label: "ID" },
                      { key: "CodigoContrato", label: "Contrato" },
                      { key: "Empleado", label: "Empleado" },
                      { key: "NumeroDocumento", label: "Documento" },
                      { key: "Obra", label: "Obra" },
                      { key: "FechaFin", label: "Fin" },
                      { key: "Semaforo", label: "Semaforo", render: (row) => <SemaforoBadge value={row.Semaforo} /> },
                      {
                        key: "documentos",
                        label: "Documentos",
                        render: (row) => (
                          <div className="row-actions">
                            <button className="ghost ghost--compact" type="button" onClick={() => abrirDocumento(`/rrhh/contratos/${row.IDcontrato}/documentos/contrato`)}>
                              Contrato
                            </button>
                            <button className="ghost ghost--compact" type="button" onClick={() => abrirDocumento(`/rrhh/contratos/${row.IDcontrato}/documentos/certificado`)}>
                              Certificado
                            </button>
                          </div>
                        )
                      }
                    ]}
                    rows={rrhhAltas}
                    empty="Todavia no hay altas de personal"
                    collapsible
                    defaultOpen={false}
                    scrollRows
                    searchable
                    searchPlaceholder="Buscar por nombre"
                  />
                </section>
              </section>
            )}

            {active === "contratos" && (
              <section className="section-grid">
                <section className="surface contratos-view-switch">
                  <div className="surface-head">
                    <div>
                      <h2>Control de contratos</h2>
                      <p className="form-help">Alterna entre el control de vigencia y la edicion de fichas del personal.</p>
                    </div>
                    <div className="inline-actions">
                      <button className={contratosVista === "contratos" ? "primary" : "ghost"} type="button" onClick={() => setContratosVista("contratos")}>
                        <CalendarClock size={16} />
                        Contratos
                      </button>
                      <button className={contratosVista === "fichas" ? "primary" : "ghost"} type="button" onClick={() => setContratosVista("fichas")}>
                        <Save size={16} />
                        Editar ficha
                      </button>
                    </div>
                  </div>
                </section>

                {contratosVista === "fichas" ? (
                  <>
                    <div className="split">
                      <form className="surface form-grid" onSubmit={buscarEmpleado}>
                        <div className="form-title">
                          <div>
                            <h2>Buscar empleado</h2>
                            <p className="form-help">Busca por DNI o nombre para cargar la ficha editable.</p>
                          </div>
                        </div>
                        <Field label="DNI o nombre" wide>
                          <input value={busqueda} onChange={(e) => setBusqueda(e.target.value)} required maxLength={80} />
                        </Field>
                        <div className="form-actions">
                          <button className="primary" disabled={saving === "busqueda"}>
                            <Search size={17} />
                            Buscar
                          </button>
                        </div>
                      </form>

                      <form className="surface form-grid" onSubmit={saveEditEmpleado}>
                        <div className="form-title">
                          <div>
                            <h2>Editar ficha</h2>
                            <p className="form-help">Los cambios quedan auditados en el historial del sistema.</p>
                          </div>
                        </div>
                        <Field label="Empleado ID">
                          <input value={editEmpleadoForm.id_empleado} readOnly />
                        </Field>
                        <Field label="Documento">
                          <input value={editEmpleadoForm.numero_documento} readOnly />
                        </Field>
                        <Field label="Nombres">
                          <input value={editEmpleadoForm.nombres} onChange={(e) => setEditEmpleadoForm({ ...editEmpleadoForm, nombres: e.target.value })} required maxLength={50} />
                        </Field>
                        <Field label="Apellido paterno">
                          <input value={editEmpleadoForm.apellido_paterno} onChange={(e) => setEditEmpleadoForm({ ...editEmpleadoForm, apellido_paterno: e.target.value })} required maxLength={50} />
                        </Field>
                        <Field label="Apellido materno">
                          <input value={editEmpleadoForm.apellido_materno} onChange={(e) => setEditEmpleadoForm({ ...editEmpleadoForm, apellido_materno: e.target.value })} required maxLength={50} />
                        </Field>
                        <Field label="Email">
                          <input value={editEmpleadoForm.email} onChange={(e) => setEditEmpleadoForm({ ...editEmpleadoForm, email: e.target.value })} type="email" required maxLength={100} />
                        </Field>
                        <Field label="Celular">
                          <input value={editEmpleadoForm.celular} onChange={(e) => setEditEmpleadoForm({ ...editEmpleadoForm, celular: e.target.value })} required maxLength={20} />
                        </Field>
                        <Field label="Area">
                          <select value={editEmpleadoForm.area} onChange={(e) => setEditEmpleadoForm({ ...editEmpleadoForm, area: e.target.value })} required>
                            <option value="">Seleccionar area</option>
                            {AREA_OPTIONS.map((area) => (
                              <option key={area} value={area}>
                                {area}
                              </option>
                            ))}
                          </select>
                        </Field>
                        <div className="form-actions">
                          <button className="primary" disabled={saving === "editar-empleado" || !editEmpleadoForm.id_empleado}>
                            <Save size={17} />
                            Guardar ficha
                          </button>
                        </div>
                      </form>
                    </div>

                    <section className="surface">
                      <h2>Resultados de busqueda</h2>
                      <GroupedDataTable
                        columns={[
                          { key: "IDempleado", label: "ID" },
                          { key: "NumeroDocumento", label: "Documento" },
                          { key: "Nombres", label: "Nombres" },
                          { key: "ApellidoPaterno", label: "Paterno" },
                          { key: "Obra", label: "Obra" },
                          { key: "EstadoContrato", label: "Contrato" },
                          { key: "accion", label: "Accion", render: (row) => <button className="ghost ghost--compact" onClick={() => cargarEdicion(row)}>Editar</button> }
                        ]}
                        rows={resultadosBusqueda}
                        empty="Busca un empleado para ver resultados"
                        collapsible={resultadosBusqueda.length > 20}
                        defaultOpen
                        scrollRows={resultadosBusqueda.length > 20}
                        searchable={resultadosBusqueda.length > 20}
                        searchPlaceholder="Buscar por nombre"
                      />
                    </section>
                  </>
                ) : (
                  <>
                <div className="split split--three">
                  <form className="surface form-grid" onSubmit={saveRenovacion}>
                    <div className="form-title">
                      <h2>Renovar contrato</h2>
                    </div>
                    <Field label="Contrato" wide>
                      <select value={renovacionForm.id_contrato} onChange={(e) => setRenovacionForm({ ...renovacionForm, id_contrato: e.target.value })} required>
                        <option value="">Seleccionar</option>
                        {contratoOptions.map((item) => (
                          <option key={String(item.IDcontrato)} value={String(item.IDcontrato)}>
                            {formatValue(item.CodigoContrato)} - {formatValue(item.Empleado)}
                          </option>
                        ))}
                      </select>
                    </Field>
                    <Field label="Nueva fecha fin">
                      <input value={renovacionForm.fecha_fin} onChange={(e) => setRenovacionForm({ ...renovacionForm, fecha_fin: e.target.value })} type="date" required />
                    </Field>
                    <div className="form-actions">
                      <button className="primary" disabled={saving === "renovacion"}>
                        <CalendarClock size={17} />
                        Renovar
                      </button>
                    </div>
                  </form>
                  <form className="surface form-grid" onSubmit={saveBoleta}>
                    <div className="form-title">
                      <h2>Boleta de cese</h2>
                    </div>
                    <Field label="Contrato" wide>
                      <select value={boletaForm.id_contrato} onChange={(e) => setBoletaForm({ ...boletaForm, id_contrato: e.target.value })} required>
                        <option value="">Seleccionar</option>
                        {rrhhContratos.map((item) => (
                          <option key={String(item.IDcontrato)} value={String(item.IDcontrato)}>
                            {formatValue(item.CodigoContrato)} - {formatValue(item.Empleado)}
                          </option>
                        ))}
                      </select>
                    </Field>
                    <Field label="Fecha cese">
                      <input value={boletaForm.fecha_cese} onChange={(e) => setBoletaForm({ ...boletaForm, fecha_cese: e.target.value })} type="date" required />
                    </Field>
                    <Field label="Motivo">
                      <select value={boletaForm.motivo} onChange={(e) => setBoletaForm({ ...boletaForm, motivo: e.target.value })}>
                        <option value="renuncia">Renuncia</option>
                        <option value="despido">Despido</option>
                      </select>
                    </Field>
                    <div className="form-actions">
                      <button className="primary" disabled={saving === "documento"}>
                        <FileText size={17} />
                        Generar boleta
                      </button>
                    </div>
                  </form>
                  <section className="surface action-panel">
                    <h2>Alertas activas</h2>
                    <div className="action-grid">
                      <article>
                        <AlertTriangle size={18} />
                        <span>Por vencer</span>
                        <strong>{formatValue(rrhhDashboard?.kpis?.contratos_por_vencer)}</strong>
                      </article>
                      <article>
                        <AlertTriangle size={18} />
                        <span>Vencidos</span>
                        <strong>{formatValue(rrhhDashboard?.kpis?.contratos_vencidos)}</strong>
                      </article>
                      <article>
                        <Users size={18} />
                        <span>Personal activo</span>
                        <strong>{formatValue(rrhhDashboard?.kpis?.personal_activo)}</strong>
                      </article>
                    </div>
                  </section>
                </div>
                <section className="surface">
                  <h2>Lista de contratos</h2>
                  <GroupedDataTable
                    columns={[
                      { key: "Semaforo", label: "Semaforo", render: (row) => <SemaforoBadge value={row.Semaforo} /> },
                      { key: "CodigoContrato", label: "Contrato" },
                      { key: "Empleado", label: "Empleado" },
                      { key: "Obra", label: "Obra" },
                      { key: "Cargo", label: "Cargo" },
                      { key: "DiasRestantes", label: "Dias" },
                      { key: "Estado", label: "Estado" },
                      {
                        key: "acciones",
                        label: "Acciones",
                        render: (row) => (
                          <div className="row-actions">
                            <button className="ghost ghost--compact action-button action-button--green" type="button" onClick={() => abrirDocumento(`/rrhh/contratos/${row.IDcontrato}/documentos/contrato`)}>
                              Contrato
                            </button>
                            <button className="ghost ghost--compact action-button action-button--green" type="button" onClick={() => abrirDocumento(`/rrhh/contratos/${row.IDcontrato}/documentos/certificado`)}>
                              Certificado
                            </button>
                            <button
                              className="ghost ghost--compact action-button action-button--yellow"
                              type="button"
                              onClick={() =>
                                abrirDocumento(
                                  `/rrhh/contratos/${row.IDcontrato}/documentos/boleta?fecha_cese=${encodeURIComponent(String(row.FechaLiquidacion ?? boletaForm.fecha_cese))}&motivo=${encodeURIComponent(boletaForm.motivo)}`
                                )
                              }
                            >
                              Boleta
                            </button>
                            <button className="ghost ghost--compact action-button action-button--red" type="button" onClick={() => liquidarContrato(row.IDcontrato)} disabled={String(row.Estado) === "liquidado"}>
                              Liquidar
                            </button>
                          </div>
                        )
                      }
                    ]}
                    rows={rrhhContratos}
                    empty="No hay contratos registrados"
                    collapsible
                    defaultOpen={false}
                    scrollRows
                    searchable
                    searchPlaceholder="Buscar por nombre"
                  />
                </section>
                <section className="surface">
                  <h2>Reporte de vigencia y bajas</h2>
                  <GroupedDataTable
                    columns={[
                      { key: "CodigoContrato", label: "Contrato" },
                      { key: "Empleado", label: "Empleado" },
                      { key: "FechaFin", label: "Fin" },
                      { key: "DiasRestantes", label: "Dias" },
                      { key: "Semaforo", label: "Semaforo", render: (row) => <SemaforoBadge value={row.Semaforo} /> },
                      { key: "TotalLiquidacion", label: "Liquidacion" }
                    ]}
                    rows={rrhhReportes.contratos_por_vencer}
                    empty="No hay contratos por vencer en los proximos 30 dias"
                    collapsible
                    defaultOpen={false}
                    scrollRows
                    searchable
                    searchPlaceholder="Buscar por nombre"
                  />
                </section>
                  </>
                )}
              </section>
            )}

            {active === "asistencia" && (
              <section className="section-grid">
                <div className="split attendance-split">
                  <form className="surface form-grid work-form" onSubmit={saveAsistencia}>
                    <div className="form-title">
                      <div>
                        <h2>Registrar asistencia</h2>
                        <p className="form-help">Busca el contrato y el sistema completa empleado y obra.</p>
                      </div>
                    </div>
                    <ContractSearchField id="asistencia-contrato" label="Contrato" value={asistenciaForm.id_contrato} contratos={contratoOptions} onChange={(idContrato) => selectContrato(idContrato, "asistencia")} />
                    <Field label="Empleado" className="field--readonly">
                      <input value={String(asistenciaContrato?.Empleado ?? "")} placeholder="Se completa con el contrato" readOnly />
                    </Field>
                    <Field label="Obra" className="field--readonly">
                      <input value={asistenciaForm.obra} placeholder="Se completa con el contrato" readOnly />
                    </Field>
                    <Field label="Fecha">
                      <input value={asistenciaForm.fecha} onChange={(e) => updateAsistencia("fecha", e.target.value)} type="date" required />
                    </Field>
                    <div className="field field--wide">
                      <span>Estado</span>
                      <div className="status-choice" role="group" aria-label="Estado de asistencia">
                        {asistenciaEstados.map((item) => (
                          <button
                            key={item.value}
                            type="button"
                            className={asistenciaForm.estado === item.value ? "active" : ""}
                            onClick={() => updateAsistencia("estado", item.value)}
                          >
                            {item.label}
                          </button>
                        ))}
                      </div>
                    </div>
                    <Field label="Horas">
                      <input value={asistenciaForm.horas} onChange={(e) => updateAsistencia("horas", e.target.value)} type="number" min="0" max="24" step="0.01" required />
                    </Field>
                    <Field label="Extras">
                      <input value={asistenciaForm.extras} onChange={(e) => updateAsistencia("extras", e.target.value)} type="number" min="0" step="0.01" />
                    </Field>
                    <Field label="Observacion" wide>
                      <textarea value={asistenciaForm.observacion} onChange={(e) => updateAsistencia("observacion", e.target.value)} maxLength={250} />
                    </Field>
                    <div className="form-actions">
                      <button className="primary" disabled={saving === "asistencia"}>
                        <Save size={17} />
                        Registrar
                      </button>
                    </div>
                  </form>

                  <form className="surface form-grid work-form" onSubmit={saveDestajo}>
                    <div className="form-title">
                      <div>
                        <h2>Ingresar destajo</h2>
                        <p className="form-help">Contrato buscable, datos de empleado y obra bloqueados.</p>
                      </div>
                    </div>
                    <ContractSearchField id="destajo-contrato" label="Contrato" value={destajoForm.id_contrato} contratos={contratoOptions} onChange={(idContrato) => selectContrato(idContrato, "destajo")} />
                    <Field label="Empleado" className="field--readonly">
                      <input value={String(destajoContrato?.Empleado ?? "")} placeholder="Se completa con el contrato" readOnly />
                    </Field>
                    <Field label="Obra" className="field--readonly">
                      <input value={destajoForm.obra} placeholder="Se completa con el contrato" readOnly />
                    </Field>
                    <Field label="Fecha">
                      <input value={destajoForm.fecha} onChange={(e) => updateDestajo("fecha", e.target.value)} type="date" required />
                    </Field>
                    <Field label="Partida">
                      <input value={destajoForm.partida} onChange={(e) => updateDestajo("partida", e.target.value)} required maxLength={120} />
                    </Field>
                    <Field label="Metrado">
                      <input value={destajoForm.metrado} onChange={(e) => updateDestajo("metrado", e.target.value)} type="number" min="0" step="0.01" required />
                    </Field>
                    <Field label="Tarifa">
                      <input value={destajoForm.tarifa} onChange={(e) => updateDestajo("tarifa", e.target.value)} type="number" min="0" step="0.01" required />
                    </Field>
                    <Field label="Observacion" wide>
                      <textarea value={destajoForm.observacion} onChange={(e) => updateDestajo("observacion", e.target.value)} maxLength={250} />
                    </Field>
                    <div className="form-actions">
                      <button className="primary" disabled={saving === "destajo"}>
                        <WalletCards size={17} />
                        Guardar destajo
                      </button>
                    </div>
                  </form>
                </div>

                <section className="surface">
                  <div className="surface-head">
                    <h2>Planilla generada</h2>
                    <button className="ghost" onClick={() => downloadExcel("planilla-maaq.xls", rrhhPlanilla)}>
                      <Download size={16} />
                      Exportar Excel
                    </button>
                  </div>
                  <GroupedDataTable
                    columns={[
                      { key: "Fecha", label: "Fecha" },
                      { key: "Empleado", label: "Empleado" },
                      { key: "Obra", label: "Obra" },
                      { key: "HorasLaboradas", label: "Horas" },
                      { key: "Jornal", label: "Jornal" },
                      { key: "Extras", label: "Extras" },
                      { key: "TotalDestajo", label: "Destajo" },
                      { key: "TotalPlanilla", label: "Total" }
                    ]}
                    rows={rrhhPlanilla}
                    empty="Registra asistencia o destajo para generar planilla"
                  />
                </section>
              </section>
            )}

            {active === "reportes" && (
              <section className="section-grid">
                <form className="surface form-grid report-builder" onSubmit={generarReporte}>
                  <div className="form-title">
                    <div>
                      <h2>Generador de reportes</h2>
                      <p className="form-help">Filtra por tipo de reporte, area, fechas, estado o busqueda libre.</p>
                    </div>
                  </div>
                  <Field label="Tipo de reporte">
                    <select value={reporteForm.tipo} onChange={(e) => updateReporte("tipo", e.target.value)}>
                      {reporteTipos.map((item) => (
                        <option key={item.value} value={item.value}>
                          {item.label}
                        </option>
                      ))}
                    </select>
                  </Field>
                  <Field label="Area">
                    <select value={reporteForm.area} onChange={(e) => updateReporte("area", e.target.value)}>
                      <option value="">Todas</option>
                      {AREA_OPTIONS.map((area) => (
                        <option key={area} value={area}>
                          {area}
                        </option>
                      ))}
                    </select>
                  </Field>
                  <Field label="Estado">
                    <select value={reporteForm.estado} onChange={(e) => updateReporte("estado", e.target.value)}>
                      <option value="">Todos</option>
                      <option value="activo">Activo</option>
                      <option value="renovado">Renovado</option>
                      <option value="liquidado">Liquidado</option>
                    </select>
                  </Field>
                  {usaMesPago ? (
                    <Field label="Mes de pago">
                      <input value={reporteForm.mes_pago} onChange={(e) => updateReporte("mes_pago", e.target.value)} type="month" />
                    </Field>
                  ) : (
                    <>
                      <Field label="Desde">
                        <input value={reporteForm.desde} onChange={(e) => updateReporte("desde", e.target.value)} type="date" />
                      </Field>
                      <Field label="Hasta">
                        <input value={reporteForm.hasta} onChange={(e) => updateReporte("hasta", e.target.value)} type="date" />
                      </Field>
                    </>
                  )}
                  {!usaMesPago && (
                    <Field label="Dias alerta">
                      <input value={reporteForm.dias} onChange={(e) => updateReporte("dias", e.target.value)} type="number" min="1" max="365" />
                    </Field>
                  )}
                  <Field label="Limite">
                    <input value={reporteForm.limit} onChange={(e) => updateReporte("limit", e.target.value)} type="number" min="1" max="5000" />
                  </Field>
                  <Field label="Buscar" wide>
                    <input value={reporteForm.q} onChange={(e) => updateReporte("q", e.target.value)} placeholder="Nombre, DNI, contrato, obra o cargo" maxLength={80} />
                  </Field>
                  <div className="form-actions report-builder__actions">
                    <button className="primary" disabled={saving === "reporte-personalizado"}>
                      <Search size={17} />
                      Generar reporte
                    </button>
                    <button className="ghost" type="button" onClick={() => descargarReportePersonalizado("excel")} disabled={!reportePersonalizado.length || saving === "reporte-excel"}>
                      <Download size={16} />
                      Excel
                    </button>
                    <button className="ghost" type="button" onClick={() => descargarReportePersonalizado("pdf")} disabled={!reportePersonalizado.length || saving === "reporte-pdf"}>
                      <FileText size={16} />
                      PDF
                    </button>
                    <button className={analisisVisible ? "primary" : "ghost"} type="button" onClick={() => setAnalisisVisible((current) => !current)}>
                      <LayoutDashboard size={16} />
                      ANALISIS ESTADISTICO
                    </button>
                  </div>
                </form>

                {analisisVisible && (
                  <section className="surface analytics-panel">
                    <div className="surface-head">
                      <div>
                        <h2>Analisis estadistico</h2>
                        <p className="form-help">Resumen visual de contratos activos, obras, alertas y costos mensuales estimados.</p>
                      </div>
                      <span className="report-count">{countLabel(analisisEstadistico.contratosActivos.length)}</span>
                    </div>
                    <div className="analytics-kpi-grid">
                      <article>
                        <span>Personal activo</span>
                        <strong>{formatValue(analisisEstadistico.personalActivo)}</strong>
                      </article>
                      <article>
                        <span>Areas con personal</span>
                        <strong>{formatValue(analisisEstadistico.totalAreas)}</strong>
                      </article>
                      <article>
                        <span>Obras activas</span>
                        <strong>{formatValue(analisisEstadistico.totalObras)}</strong>
                      </article>
                      <article>
                        <span>Costo mensual estimado</span>
                        <strong>{formatMoney(analisisEstadistico.totalCostoMensual)}</strong>
                      </article>
                    </div>
                    <div className="chart-grid">
                      <ChartCard title="Contratos por area" detail="Grafico de barras para comparar la carga de personal por departamento.">
                        <BarChart data={analisisEstadistico.contratosPorArea} />
                      </ChartCard>
                      <ChartCard title="Semaforo de contratos" detail="Grafico circular segun estado de vencimiento y alerta.">
                        <PieChart data={analisisEstadistico.semaforoContratos} />
                      </ChartCard>
                      <ChartCard title="Altas por mes" detail="Grafico de lineas con la evolucion de ingresos de personal.">
                        <LineChart data={analisisEstadistico.altasPorMes} />
                      </ChartCard>
                      <ChartCard title="Bajas por mes" detail="Grafico de lineas con contratos liquidados segun fecha de baja.">
                        <LineChart data={analisisEstadistico.bajasPorMes} />
                      </ChartCard>
                      <ChartCard title="Contratos por obra" detail="Ranking de obras con mayor cantidad de trabajadores asignados.">
                        <BarChart data={analisisEstadistico.contratosPorObra} />
                      </ChartCard>
                      <ChartCard title="Costo mensual por area" detail="Estimacion calculada desde el jornal diario registrado en cada contrato activo.">
                        <BarChart data={analisisEstadistico.costoMensualPorArea} valueLabel="S/" />
                      </ChartCard>
                    </div>
                  </section>
                )}

                <section className="surface report-surface">
                  <div className="surface-head">
                    <h2>Resultado del reporte</h2>
                    <span className="report-count">{countLabel(reportePersonalizado.length)}</span>
                  </div>
                  {reportePersonalizado.length > 0 && (
                    <div className="report-model">
                      <div className="report-model__cover">
                        <span>Modelo de reporte</span>
                        <h3>{reporteTitulo}</h3>
                        <p>Resumen ejecutivo, filtros aplicados y detalle operativo agrupado por area.</p>
                      </div>
                      <div className="report-kpi-grid">
                        {reporteKpis.map((item) => (
                          <article className={`report-kpi report-kpi--${item.tone}`} key={`${item.label}-${item.value}`}>
                            <span>{item.label}</span>
                            <strong>{item.value}</strong>
                          </article>
                        ))}
                      </div>
                      <div className="report-filter-strip">
                        <span>Area: <strong>{reporteForm.area || "Todas"}</strong></span>
                        <span>Estado: <strong>{reporteForm.estado || "Todos"}</strong></span>
                        <span>Desde: <strong>{reporteForm.desde || "-"}</strong></span>
                        <span>Hasta: <strong>{reporteForm.hasta || "-"}</strong></span>
                        <span>Mes: <strong>{usaMesPago ? reporteForm.mes_pago : "-"}</strong></span>
                        <span>Busqueda: <strong>{reporteForm.q || "-"}</strong></span>
                      </div>
                      <div className="report-area-summary">
                        {reporteResumen.areas.slice(0, 8).map((area) => (
                          <span key={area.area}>
                            {area.area}
                            <strong>{countLabel(area.registros)}</strong>
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  <GroupedDataTable
                    columns={reportePersonalizadoColumns}
                    rows={reportePersonalizado}
                    empty="Genera un reporte para ver resultados"
                    collapsible={reportePersonalizado.length > 80}
                    defaultOpen
                    scrollRows={reportePersonalizado.length > 80}
                    searchable={reportePersonalizado.length > 80}
                    searchPlaceholder="Filtrar por nombre"
                  />
                </section>

                <div className="report-sections">
                  <section className="surface report-surface">
                    <div className="surface-head">
                      <h2>Personal activo por area</h2>
                      <span className="report-count">{countLabel(rrhhReportes.personal_activo.length)}</span>
                    </div>
                    <GroupedDataTable
                      columns={[
                        { key: "Empleado", label: "Empleado" },
                        { key: "NumeroDocumento", label: "Documento" },
                        { key: "Obra", label: "Obra" },
                        { key: "Cargo", label: "Cargo" },
                        { key: "FechaFin", label: "Fin" }
                      ]}
                      rows={rrhhReportes.personal_activo}
                      empty="No hay personal activo"
                      collapsible
                      defaultOpen={false}
                      scrollRows
                      searchable
                      searchPlaceholder="Buscar por nombre"
                    />
                  </section>
                  <section className="surface report-surface">
                    <div className="surface-head">
                      <h2>Planilla total por area</h2>
                      <span className="report-count">{countLabel(rrhhReportes.planilla_total.length)}</span>
                    </div>
                    <GroupedDataTable
                      columns={[
                        { key: "Empleado", label: "Empleado" },
                        { key: "Jornal", label: "Jornal" },
                        { key: "Extras", label: "Extras" },
                        { key: "TotalDestajo", label: "Destajo" },
                        { key: "TotalPlanilla", label: "Total" }
                      ]}
                      rows={rrhhReportes.planilla_total}
                      empty="No hay planilla acumulada"
                    />
                  </section>
                </div>

                <section className="surface">
                  <h2>Historial auditado</h2>
                  <DataTable
                    columns={[
                      { key: "IDaudit", label: "ID" },
                      { key: "Modulo", label: "Modulo" },
                      { key: "Accion", label: "Accion" },
                      { key: "Entidad", label: "Entidad" },
                      { key: "Descripcion", label: "Descripcion" },
                      { key: "Fecha", label: "Fecha" }
                    ]}
                    rows={rrhhAuditoria}
                    empty="No hay historial RRHH"
                  />
                </section>
              </section>
            )}
          </div>
        </div>
      </main>
      {documentoActual && (
        <div className="document-modal" role="dialog" aria-modal="true" aria-label="Documento generado">
          <section className="document-modal__panel">
            <header className="document-modal__head">
              <div>
                <p className="eyebrow">Documento generado</p>
                <h2>{documentoActual.filename}</h2>
              </div>
              <div className="inline-actions">
                <button className="ghost" type="button" onClick={imprimirDocumento}>
                  <FileText size={16} />
                  Imprimir / PDF
                </button>
                {documentoPdfPath && (
                  <button
                    className="ghost"
                    type="button"
                    onClick={() => descargarPdf(documentoPdfPath, documentoActual.filename.replace(/\.html$/i, ".pdf"))}
                    disabled={saving === "pdf"}
                  >
                    <Download size={16} />
                    Descargar PDF
                  </button>
                )}
                <button className="ghost" type="button" onClick={descargarDocumentoHtml}>
                  <Download size={16} />
                  HTML
                </button>
                <button className="primary" type="button" onClick={() => setDocumentoActual(null)}>
                  Cerrar
                </button>
              </div>
            </header>
            <iframe id="documento-preview" title={documentoActual.filename} srcDoc={documentoActual.html} />
          </section>
        </div>
      )}
    </div>
  );
}
