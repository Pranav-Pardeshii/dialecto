import type { paths } from "./schema";

export class ApiError extends Error {
  code: string;
  details: Record<string, unknown>;
  requestId: string;
  statusCode: number;

  constructor(code: string, message: string, statusCode: number, details = {}, requestId = "") {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.statusCode = statusCode;
    this.details = details;
    this.requestId = requestId;
  }
}

// Current demo user stored in localStorage (default to Aarav: ID 1)
const DEMO_USER_STORAGE_KEY = "dialecto_demo_user_id";

export function getActiveDemoUserId(): number {
  if (typeof window === "undefined") return 1;
  const saved = localStorage.getItem(DEMO_USER_STORAGE_KEY);
  return saved ? parseInt(saved, 10) : 1;
}

export function setActiveDemoUserId(userId: number): void {
  if (typeof window !== "undefined") {
    localStorage.setItem(DEMO_USER_STORAGE_KEY, userId.toString());
  }
}

export async function apiFetch<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const userId = getActiveDemoUserId();
  const headers = new Headers(options.headers || {});
  headers.set("Content-Type", "application/json");
  headers.set("X-Demo-User-Id", userId.toString());

  const response = await fetch(endpoint, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errorData: { error?: { code?: string; message?: string; details?: Record<string, unknown>; request_id?: string } } = {};
    try {
      errorData = await response.json();
    } catch {
      // Non-json error response
    }
    const err = errorData.error;
    throw new ApiError(
      err?.code || "unknown_error",
      err?.message || `Request failed with status ${response.status}`,
      response.status,
      err?.details || {},
      err?.request_id || response.headers.get("X-Request-Id") || ""
    );
  }

  return response.json() as Promise<T>;
}

export type User = paths["/api/v1/users"]["get"]["responses"][200]["content"]["application/json"][number];
export type ConceptGraph = paths["/api/v1/concepts"]["get"]["responses"][200]["content"]["application/json"];
export type ConceptNode = ConceptGraph["nodes"][number];
export type ConceptEdge = ConceptGraph["edges"][number];
export type ConceptDetail = paths["/api/v1/concepts/{concept_id}"]["get"]["responses"][200]["content"]["application/json"];

export type PracticeNextResponse = paths["/api/v1/practice/next"]["post"]["responses"][200]["content"]["application/json"];
export type PracticeAnswerRequest = paths["/api/v1/practice/answers"]["post"]["requestBody"]["content"]["application/json"];
export type PracticeAnswerResponse = paths["/api/v1/practice/answers"]["post"]["responses"][200]["content"]["application/json"];

export type DiagnosticStartResponse = paths["/api/v1/diagnostic/sessions"]["post"]["responses"][200]["content"]["application/json"];
export type DiagnosticAnswerRequest = paths["/api/v1/diagnostic/sessions/{session_id}/answers"]["post"]["requestBody"]["content"]["application/json"];
export type DiagnosticAnswerResponse = paths["/api/v1/diagnostic/sessions/{session_id}/answers"]["post"]["responses"][200]["content"]["application/json"];
export type DiagnosticResultResponse = paths["/api/v1/diagnostic/sessions/{session_id}/result"]["get"]["responses"][200]["content"]["application/json"];

export type LearnerMasteryItem = paths["/api/v1/learner/mastery"]["get"]["responses"][200]["content"]["application/json"][number];
export type LearnerSummary = paths["/api/v1/learner/summary"]["get"]["responses"][200]["content"]["application/json"];

export type LLMStatsResponse = paths["/api/v1/ops/llm-stats"]["get"]["responses"][200]["content"]["application/json"];

export type TeachbackSessionStartResponse = paths["/api/v1/teachback/sessions"]["post"]["responses"][200]["content"]["application/json"];
export type TeachbackTurnResponse = paths["/api/v1/teachback/sessions/{session_id}/turns"]["post"]["responses"][200]["content"]["application/json"];
export type TeachbackDetailResponse = paths["/api/v1/teachback/sessions/{session_id}"]["get"]["responses"][200]["content"]["application/json"];

export type ReviewDueItem = paths["/api/v1/reviews/due"]["get"]["responses"][200]["content"]["application/json"][number];

export type TeacherHeatmapResponse = paths["/api/v1/teacher/classrooms/{classroom_id}/heatmap"]["get"]["responses"][200]["content"]["application/json"];
export type CurriculumGapItem = paths["/api/v1/teacher/classrooms/{classroom_id}/gaps"]["get"]["responses"][200]["content"]["application/json"][number];
export type MisconceptionPrevalenceItem = paths["/api/v1/teacher/classrooms/{classroom_id}/misconceptions"]["get"]["responses"][200]["content"]["application/json"][number];
export type AtRiskStudentItem = paths["/api/v1/teacher/classrooms/{classroom_id}/at-risk"]["get"]["responses"][200]["content"]["application/json"][number];
export type StudentDetailResponse = paths["/api/v1/teacher/classrooms/{classroom_id}/students/{student_id}"]["get"]["responses"][200]["content"]["application/json"];

// Authoring types
export type QuestionAuthoringItem = paths["/api/v1/authoring/questions"]["get"]["responses"][200]["content"]["application/json"]["questions"][number];
export type QuestionGenerateRequest = paths["/api/v1/authoring/questions/generate"]["post"]["requestBody"]["content"]["application/json"];
export type QuestionGenerateResponse = paths["/api/v1/authoring/questions/generate"]["post"]["responses"][200]["content"]["application/json"];
export type QuestionCreateRequest = paths["/api/v1/authoring/questions"]["post"]["requestBody"]["content"]["application/json"];
export type QuestionUpdateRequest = paths["/api/v1/authoring/questions/{question_id}"]["put"]["requestBody"]["content"]["application/json"];

// Explainable mastery types
export type ExplainableMasteryResponse = paths["/api/v1/learner/concepts/{concept_id}/explainable"]["get"]["responses"][200]["content"]["application/json"];

// Intervention types
export type InterventionRecommendation = paths["/api/v1/teacher/classrooms/{classroom_id}/interventions/recommendations"]["get"]["responses"][200]["content"]["application/json"][number];
export type InterventionDetail = paths["/api/v1/teacher/classrooms/{classroom_id}/interventions/{intervention_id}"]["get"]["responses"][200]["content"]["application/json"];
export type InterventionCreateRequest = paths["/api/v1/teacher/classrooms/{classroom_id}/interventions"]["post"]["requestBody"]["content"]["application/json"];
export type InterventionOutcomes = paths["/api/v1/teacher/classrooms/{classroom_id}/interventions/{intervention_id}/outcomes"]["get"]["responses"][200]["content"]["application/json"];
export type StudentIntervention = paths["/api/v1/learner/interventions"]["get"]["responses"][200]["content"]["application/json"][number];

// Diagram types
export interface DiagramStructure {
  id: string;
  name: string;
  aliases?: string[];
  description?: string;
  function?: string;
  color?: string;
  oxygenated?: boolean | null;
  related_misconception_id?: string | null;
}

export interface DiagramAssessmentItem {
  id: string;
  type: string;
  prompt: string;
  target_structure_id?: string;
  target_sequence?: string[];
  hint?: string;
  rubric?: string;
  rubric_points?: string[];
}

export interface DiagramManifest {
  id: string;
  concept_id: string;
  chapter: string;
  display_name: string;
  subtitle: string;
  model_type: string;
  structures: DiagramStructure[];
  pathways?: Array<{ id: string; name: string; description: string; ordered_structure_ids: string[] }>;
  assessments: DiagramAssessmentItem[];
  licence?: {
    source: string;
    creator: string;
    licence_type: string;
    attribution: string;
  };
}

export type VoiceCommandResponse = paths["/api/v1/diagrams/{diagram_id}/commands"]["post"]["responses"][200]["content"]["application/json"];

export interface DiagramAssessmentResponse {
  is_correct: boolean;
  score: number;
  feedback: string;
  target_structure_id?: string | null;
  target_sequence?: string[] | null;
  mastery: { concept_id: string; before: number; after: number };
  detected_misconception?: { id: string } | null;
  is_idempotent_replay?: boolean;
}

export type DiagramAssessmentSubmitRequest = paths["/api/v1/diagrams/{diagram_id}/assessments"]["post"]["requestBody"]["content"]["application/json"];

export const api = {
  getUsers: (includeSimulated = false) =>
    apiFetch<User[]>(`/api/v1/users?include_simulated=${includeSimulated}`),
  getMe: () => apiFetch<User>("/api/v1/me"),
  getHealth: () => apiFetch<{ status: string }>("/health"),
  getReady: () => apiFetch<{ status: string; database: string }>("/ready"),
  getConceptGraph: () => apiFetch<ConceptGraph>("/api/v1/concepts"),
  getConceptDetail: (conceptId: string) =>
    apiFetch<ConceptDetail>(`/api/v1/concepts/${conceptId}`),

  // Practice
  getPracticeNext: (mode = "adaptive", conceptId?: string) =>
    apiFetch<PracticeNextResponse>("/api/v1/practice/next", {
      method: "POST",
      body: JSON.stringify({ mode, concept_id: conceptId || null }),
    }),
  submitPracticeAnswer: (req: PracticeAnswerRequest) =>
    apiFetch<PracticeAnswerResponse>("/api/v1/practice/answers", {
      method: "POST",
      body: JSON.stringify(req),
    }),

  // Diagnostic
  startDiagnostic: () =>
    apiFetch<DiagnosticStartResponse>("/api/v1/diagnostic/sessions", {
      method: "POST",
    }),
  submitDiagnosticAnswer: (sessionId: number, req: DiagnosticAnswerRequest) =>
    apiFetch<DiagnosticAnswerResponse>(`/api/v1/diagnostic/sessions/${sessionId}/answers`, {
      method: "POST",
      body: JSON.stringify(req),
    }),
  getDiagnosticResult: (sessionId: number) =>
    apiFetch<DiagnosticResultResponse>(`/api/v1/diagnostic/sessions/${sessionId}/result`),

  // Teach-Back with Pip
  startTeachback: (conceptId: string) =>
    apiFetch<TeachbackSessionStartResponse>("/api/v1/teachback/sessions", {
      method: "POST",
      body: JSON.stringify({ concept_id: conceptId }),
    }),
  submitTeachbackTurn: (sessionId: number, content: string) =>
    apiFetch<TeachbackTurnResponse>(`/api/v1/teachback/sessions/${sessionId}/turns`, {
      method: "POST",
      body: JSON.stringify({ content }),
    }),
  getTeachbackSession: (sessionId: number) =>
    apiFetch<TeachbackDetailResponse>(`/api/v1/teachback/sessions/${sessionId}`),

  // Reviews
  getDueReviews: () => apiFetch<ReviewDueItem[]>("/api/v1/reviews/due"),

  // Teacher Analytics
  getTeacherHeatmap: (classroomId = 1) =>
    apiFetch<TeacherHeatmapResponse>(`/api/v1/teacher/classrooms/${classroomId}/heatmap`),
  getTeacherGaps: (classroomId = 1) =>
    apiFetch<CurriculumGapItem[]>(`/api/v1/teacher/classrooms/${classroomId}/gaps`),
  getTeacherMisconceptions: (classroomId = 1) =>
    apiFetch<MisconceptionPrevalenceItem[]>(`/api/v1/teacher/classrooms/${classroomId}/misconceptions`),
  getTeacherAtRisk: (classroomId = 1) =>
    apiFetch<AtRiskStudentItem[]>(`/api/v1/teacher/classrooms/${classroomId}/at-risk`),
  getTeacherStudentDetail: (studentId: number, classroomId = 1) =>
    apiFetch<StudentDetailResponse>(`/api/v1/teacher/classrooms/${classroomId}/students/${studentId}`),

  // Learner
  getLearnerMastery: () => apiFetch<LearnerMasteryItem[]>("/api/v1/learner/mastery"),
  getLearnerSummary: () => apiFetch<LearnerSummary>("/api/v1/learner/summary"),

  // Explainable Mastery
  getConceptExplainableMastery: (conceptId: string) =>
    apiFetch<ExplainableMasteryResponse>(`/api/v1/learner/concepts/${conceptId}/explainable`),
  getTeacherStudentExplainableMastery: (studentId: number, conceptId: string, classroomId = 1) =>
    apiFetch<ExplainableMasteryResponse>(
      `/api/v1/teacher/classrooms/${classroomId}/students/${studentId}/concepts/${conceptId}/explainable`
    ),

  // Question Authoring & Pipeline
  getAuthoringQuestions: (params?: { concept_id?: string; review_status?: string; kind?: string }) => {
    const q = new URLSearchParams();
    if (params?.concept_id) q.set("concept_id", params.concept_id);
    if (params?.review_status) q.set("review_status", params.review_status);
    if (params?.kind) q.set("kind", params.kind);
    return apiFetch<{ questions: QuestionAuthoringItem[]; total: number }>(`/api/v1/authoring/questions?${q.toString()}`);
  },
  generateQuestions: (req: QuestionGenerateRequest) =>
    apiFetch<QuestionGenerateResponse>("/api/v1/authoring/questions/generate", {
      method: "POST",
      body: JSON.stringify(req),
    }),
  createQuestionDraft: (req: QuestionCreateRequest) =>
    apiFetch<QuestionAuthoringItem>("/api/v1/authoring/questions", {
      method: "POST",
      body: JSON.stringify(req),
    }),
  updateQuestionDraft: (questionId: string, req: QuestionUpdateRequest) =>
    apiFetch<QuestionAuthoringItem>(`/api/v1/authoring/questions/${questionId}`, {
      method: "PUT",
      body: JSON.stringify(req),
    }),
  reviewQuestion: (questionId: string, action: "approve" | "reject", rejectionReason?: string) =>
    apiFetch<QuestionAuthoringItem>(`/api/v1/authoring/questions/${questionId}/review`, {
      method: "POST",
      body: JSON.stringify({ action, rejection_reason: rejectionReason || null }),
    }),
  deleteQuestionDraft: (questionId: string) =>
    apiFetch<void>(`/api/v1/authoring/questions/${questionId}`, {
      method: "DELETE",
    }),

  // Teacher Interventions
  getInterventionRecommendations: (classroomId = 1) =>
    apiFetch<InterventionRecommendation[]>(`/api/v1/teacher/classrooms/${classroomId}/interventions/recommendations`),
  getInterventions: (classroomId = 1, statusFilter?: string) => {
    const query = statusFilter ? `?status_filter=${statusFilter}` : "";
    return apiFetch<InterventionDetail[]>(`/api/v1/teacher/classrooms/${classroomId}/interventions${query}`);
  },
  createIntervention: (req: InterventionCreateRequest, classroomId = 1) =>
    apiFetch<InterventionDetail>(`/api/v1/teacher/classrooms/${classroomId}/interventions`, {
      method: "POST",
      body: JSON.stringify(req),
    }),
  assignIntervention: (interventionId: number, studentIds: number[], classroomId = 1) =>
    apiFetch<InterventionDetail>(`/api/v1/teacher/classrooms/${classroomId}/interventions/${interventionId}/assign`, {
      method: "POST",
      body: JSON.stringify({ student_ids: studentIds }),
    }),
  getInterventionOutcomes: (interventionId: number, classroomId = 1) =>
    apiFetch<InterventionOutcomes>(`/api/v1/teacher/classrooms/${classroomId}/interventions/${interventionId}/outcomes`),

  // Student Interventions
  getMyInterventions: () => apiFetch<StudentIntervention[]>("/api/v1/learner/interventions"),
  completeMyIntervention: (assignmentId: number) =>
    apiFetch<void>(`/api/v1/learner/interventions/${assignmentId}/complete`, {
      method: "POST",
    }),

  // Interactive Biology Lab & Voice
  getDiagrams: () => apiFetch<Record<string, unknown>[]>("/api/v1/diagrams"),
  getDiagramManifest: (diagramId: string) =>
    apiFetch<DiagramManifest>(`/api/v1/diagrams/${diagramId}`),
  sendDiagramVoiceCommand: (
    diagramId: string,
    spokenText: string,
    isAssessmentMode = false,
    activeQuestionId?: string
  ) =>
    apiFetch<VoiceCommandResponse>(`/api/v1/diagrams/${diagramId}/commands`, {
      method: "POST",
      body: JSON.stringify({
        diagram_id: diagramId,
        spoken_text: spokenText,
        is_assessment_mode: isAssessmentMode,
        active_question_id: activeQuestionId || null,
      }),
    }),
  submitDiagramAssessment: (diagramId: string, req: DiagramAssessmentSubmitRequest) =>
    apiFetch<DiagramAssessmentResponse>(`/api/v1/diagrams/${diagramId}/assessments`, {
      method: "POST",
      body: JSON.stringify(req),
    }),

  // Ops & Telemetry
  getLLMStats: () => apiFetch<LLMStatsResponse>("/api/v1/ops/llm-stats"),
};
