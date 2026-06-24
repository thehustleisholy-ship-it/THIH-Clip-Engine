export const MOMENT_TYPES = [
  "Strong Opening Conviction",
  "Scripture Explanation",
  "Practical Application",
  "Repentance / Heart-Check",
  "Memorable Quote",
  "Leadership / Work / Stewardship",
  "Prayer or Invitation",
] as const;

export const CONTENT_MODES = [
  { value: "sermon", label: "Sermon" },
  { value: "devotional", label: "Devotional" },
  { value: "podcast", label: "Podcast" },
  { value: "teaching", label: "Teaching" },
  { value: "testimony", label: "Testimony" },
  { value: "thih_systems", label: "THIH Systems" },
  { value: "business_thought_leadership", label: "Business Thought Leadership" },
] as const;

export const DURATION_MODES = ["30-60 seconds", "30-90 seconds", "custom"] as const;

export const AVOIDANCE_CHECKLIST = [
  "does not start mid-sentence",
  "does not end without resolution",
  "does not have weak first 3 seconds",
  "does not duplicate another selected clip",
  "does not misrepresent the sermon",
  "does not run over 90 seconds unless needed",
] as const;

export type MomentType = (typeof MOMENT_TYPES)[number];
export type DurationMode = (typeof DURATION_MODES)[number];

export interface SermonMetadata {
  sermonTitle: string;
  scriptureReference: string;
  coreTheme: string;
  totalDuration: string;
  contentMode: string;
  selectionInstructions: string;
}

export interface FactoryClip {
  id: string;
  start_time: string;
  end_time: string;
  duration: number;
  text: string;
  clip_order: number;
  relevance_score: number;
  video_url: string;
  thih_score?: number;
  thih?: Record<string, number | string | null>;
  platform_fit?: string[];
  recommended_title?: string | null;
  recommended_caption?: string | null;
  recommended_cta?: string | null;
  recommended_hashtags?: string[];
  scripture_reference?: string | null;
  content_mode?: string | null;
}

export interface ClipFactoryState {
  momentType: MomentType;
  startTime: string;
  endTime: string;
  durationMode: DurationMode;
  checklist: Record<string, boolean>;
  selectedTitle: string;
  cta: string;
  hashtags: string;
}

export function parseTimeToSeconds(value: string): number | null {
  const normalized = value.trim();
  if (!normalized) return null;
  if (/^\d+(\.\d+)?$/.test(normalized)) return Number(normalized);
  const parts = normalized.split(":").map((part) => part.trim());
  if (parts.length < 2 || parts.length > 3) return null;
  if (parts.some((part) => !/^\d+$/.test(part))) return null;
  const numbers = parts.map(Number);
  if (numbers.some((part) => Number.isNaN(part))) return null;
  if (numbers.length === 2) return numbers[0] * 60 + numbers[1];
  return numbers[0] * 3600 + numbers[1] * 60 + numbers[2];
}

export function formatSeconds(seconds: number): string {
  const safeSeconds = Math.max(0, Math.round(seconds));
  const hours = Math.floor(safeSeconds / 3600);
  const minutes = Math.floor((safeSeconds % 3600) / 60);
  const remainder = safeSeconds % 60;
  if (hours > 0) {
    return `${hours}:${String(minutes).padStart(2, "0")}:${String(remainder).padStart(2, "0")}`;
  }
  return `${minutes}:${String(remainder).padStart(2, "0")}`;
}

export function getDurationSeconds(startTime: string, endTime: string): number | null {
  const start = parseTimeToSeconds(startTime);
  const end = parseTimeToSeconds(endTime);
  if (start === null || end === null || end <= start) return null;
  return end - start;
}

export function validateDuration(startTime: string, endTime: string, durationMode: DurationMode): string | null {
  const duration = getDurationSeconds(startTime, endTime);
  if (duration === null) return "End time must be greater than start time.";
  if (durationMode === "30-60 seconds" && (duration < 30 || duration > 60)) {
    return "Duration should be between 30 and 60 seconds.";
  }
  if (durationMode === "30-90 seconds" && (duration < 30 || duration > 90)) {
    return "Duration should be between 30 and 90 seconds.";
  }
  return null;
}

export function createDefaultClipState(clip: FactoryClip): ClipFactoryState {
  const fallbackTitle = clip.recommended_title || `Clip ${clip.clip_order}: ${clip.text.slice(0, 48)}`;
  return {
    momentType: "Strong Opening Conviction",
    startTime: clip.start_time,
    endTime: clip.end_time,
    durationMode: "30-90 seconds",
    checklist: Object.fromEntries(AVOIDANCE_CHECKLIST.map((item) => [item, false])),
    selectedTitle: fallbackTitle,
    cta: clip.recommended_cta || "Save this and share it with someone building with purpose.",
    hashtags: (clip.recommended_hashtags?.length ? clip.recommended_hashtags : ["#THIH", "#SermonClips", "#FaithAndWork"]).join(" "),
  };
}

export function getTitleOptions(clip: FactoryClip, metadata: SermonMetadata, momentType: string): string[] {
  return Array.from(
    new Set(
      [
        clip.recommended_title || "",
        metadata.coreTheme ? `${metadata.coreTheme}: ${momentType}` : "",
        metadata.scriptureReference ? `${momentType}: ${metadata.scriptureReference}` : "",
      ].filter(Boolean),
    ),
  );
}

export function buildCaptionPacket(clip: FactoryClip, state: ClipFactoryState, metadata: SermonMetadata): string {
  const scripture = metadata.scriptureReference || clip.scripture_reference || "Scripture reference TBD";
  return [
    `Title: ${state.selectedTitle}`,
    `Trim: ${state.startTime} - ${state.endTime}`,
    `Scripture: ${scripture}`,
    `Moment Type: ${state.momentType}`,
    `Caption: ${clip.recommended_caption || metadata.coreTheme || clip.text}`,
    `CTA: ${state.cta}`,
    `Hashtags: ${state.hashtags}`,
  ].join("\n");
}

export function buildSelectionInstructions(metadata: SermonMetadata): string {
  return `Select sermon clips for ${metadata.sermonTitle || "this sermon"}. Prioritize ${metadata.coreTheme || "clear conviction, service value, and message integrity"}. Use ${metadata.scriptureReference || "the central Scripture"} as the canon-fit anchor. Choose distinct 30-90 second moments that open clearly, resolve cleanly, avoid duplicate ranges, and preserve the sermon context. Content mode: ${metadata.contentMode}. ${metadata.selectionInstructions || ""}`.trim();
}

export function buildManualClippingBrief(metadata: SermonMetadata): string {
  return `Manual clipping brief\nSermon: ${metadata.sermonTitle || "Untitled sermon"}\nScripture: ${metadata.scriptureReference || "TBD"}\nTheme: ${metadata.coreTheme || "TBD"}\nDuration: ${metadata.totalDuration || "TBD"}\n\nFind moments with a strong first 3 seconds, a complete thought, no mid-sentence start, no unresolved ending, and no duplicate timing windows. Package each approved clip with title options, CTA, hashtags, moment type, and platform fit.`;
}