"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Check, Clipboard, LayoutGrid, ListChecks, Save, Wand2 } from "lucide-react";

import { AlgorithmPrinciples } from "./algorithm-principles";
import { AIInstructions } from "./ai-instructions";
import { ClipBuilder } from "./clip-builder";
import { SermonSetup } from "./sermon-setup";
import {
  buildSelectionInstructions,
  createDefaultClipState,
  formatSeconds,
  getDurationSeconds,
  parseTimeToSeconds,
  validateDuration,
  type ClipFactoryState,
  type FactoryClip,
  type SermonMetadata,
} from "@/lib/shorts-factory";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";

interface FactoryTask {
  id: string;
  source_title?: string | null;
  status?: string | null;
  font_family?: string | null;
  font_size?: number | null;
  font_color?: string | null;
  caption_template?: string | null;
  include_broll?: boolean | null;
  cut_long_pauses?: boolean | null;
  pause_threshold_ms?: number | null;
  remove_filler_words?: boolean | null;
  filtered_words?: string[] | null;
  content_mode?: string | null;
  selection_instructions?: string | null;
}

type FactoryTab = "principles" | "setup" | "builder" | "instructions";

const tabs: Array<{ id: FactoryTab; label: string; icon: typeof ListChecks }> = [
  { id: "principles", label: "Algorithm Principles", icon: ListChecks },
  { id: "setup", label: "Sermon Setup", icon: LayoutGrid },
  { id: "builder", label: "Clip Builder", icon: Wand2 },
  { id: "instructions", label: "AI Instructions", icon: Clipboard },
];

function getTaskDuration(clips: FactoryClip[]) {
  const maxEnd = clips.reduce((max, clip) => {
    const end = parseTimeToSeconds(clip.end_time) ?? 0;
    return Math.max(max, end);
  }, 0);
  return maxEnd ? formatSeconds(maxEnd) : "";
}

function buildInitialStates(clips: FactoryClip[]) {
  return Object.fromEntries(clips.map((clip) => [clip.id, createDefaultClipState(clip)]));
}

async function parseError(response: Response) {
  try {
    const data = await response.json();
    if (typeof data.detail === "string") return data.detail;
    if (data.detail?.message) return data.detail.message;
  } catch {
    // fall through
  }
  return `Request failed with status ${response.status}`;
}

interface ShortsFactoryProps {
  task: FactoryTask;
  clips: FactoryClip[];
  onRefresh: () => Promise<void>;
}

export function ShortsFactory({ task, clips, onRefresh }: ShortsFactoryProps) {
  const [activeTab, setActiveTab] = useState<FactoryTab>("builder");
  const [selectedClipId, setSelectedClipId] = useState<string | null>(clips[0]?.id ?? null);
  const [clipStates, setClipStates] = useState<Record<string, ClipFactoryState>>(() => buildInitialStates(clips));
  const [metadata, setMetadata] = useState<SermonMetadata>({
    sermonTitle: task.source_title || "",
    scriptureReference: clips.find((clip) => clip.scripture_reference)?.scripture_reference || "",
    coreTheme: "",
    totalDuration: getTaskDuration(clips),
    contentMode: task.content_mode || clips[0]?.content_mode || "sermon",
    selectionInstructions: task.selection_instructions || "",
  });
  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSavingSettings, setIsSavingSettings] = useState(false);
  const [isSavingTrim, setIsSavingTrim] = useState(false);

  const selectedClip = useMemo(
    () => clips.find((clip) => clip.id === selectedClipId) || clips[0],
    [clips, selectedClipId],
  );

  const handleStateChange = (clipId: string, state: ClipFactoryState) => {
    setClipStates((current) => ({ ...current, [clipId]: state }));
  };

  const handleCopy = async (key: string, value: string) => {
    await navigator.clipboard.writeText(value);
    setCopiedKey(key);
    window.setTimeout(() => setCopiedKey((current) => (current === key ? null : current)), 1600);
  };

  const saveTaskSettings = async (nextMetadata = metadata) => {
    setIsSavingSettings(true);
    setError(null);
    const selectionInstructions = buildSelectionInstructions(nextMetadata);
    try {
      const response = await fetch(`/api/tasks/${task.id}/settings`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          font_family: task.font_family || "TikTokSans-Regular",
          font_size: task.font_size || 24,
          font_color: task.font_color || "#FFFFFF",
          caption_template: task.caption_template || "default",
          include_broll: Boolean(task.include_broll),
          apply_to_existing: false,
          cut_long_pauses: Boolean(task.cut_long_pauses),
          pause_threshold_ms: task.pause_threshold_ms || 900,
          remove_filler_words: Boolean(task.remove_filler_words),
          filtered_words: task.filtered_words || [],
          content_mode: nextMetadata.contentMode,
          selection_instructions: selectionInstructions,
        }),
      });
      if (!response.ok) throw new Error(await parseError(response));
      setMetadata((current) => ({ ...current, selectionInstructions }));
      setNotice("Shorts Factory instructions saved for future analysis.");
      await onRefresh();
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Unable to save Shorts Factory settings.");
    } finally {
      setIsSavingSettings(false);
    }
  };

  const saveTrim = async (clip: FactoryClip, state: ClipFactoryState) => {
    const trimError = validateDuration(state.startTime, state.endTime, state.durationMode);
    if (trimError) {
      setError(trimError);
      return;
    }

    const clipStart = parseTimeToSeconds(clip.start_time) ?? 0;
    const clipEnd = parseTimeToSeconds(clip.end_time) ?? clipStart + clip.duration;
    const nextStart = parseTimeToSeconds(state.startTime);
    const nextEnd = parseTimeToSeconds(state.endTime);
    if (nextStart === null || nextEnd === null || nextStart < clipStart || nextEnd > clipEnd) {
      setError(`Trim range must stay inside ${clip.start_time} - ${clip.end_time}.`);
      return;
    }

    setIsSavingTrim(true);
    setError(null);
    try {
      const response = await fetch(`/api/tasks/${task.id}/clips/${clip.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          start_offset: Math.max(0, nextStart - clipStart),
          end_offset: Math.max(0, clipEnd - nextEnd),
        }),
      });
      if (!response.ok) throw new Error(await parseError(response));
      const duration = getDurationSeconds(state.startTime, state.endTime);
      setNotice(`Trim saved${duration ? ` at ${formatSeconds(duration)}` : ""}.`);
      await onRefresh();
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Unable to save trim.");
    } finally {
      setIsSavingTrim(false);
    }
  };

  return (
    <main className="min-h-screen bg-neutral-50 text-neutral-950">
      <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
        <div className="mb-6 flex flex-wrap items-center justify-between gap-4 border-b border-neutral-200 pb-5">
          <div>
            <Link href={`/tasks/${task.id}`} className="mb-3 inline-flex items-center gap-2 text-sm text-neutral-600 hover:text-neutral-950">
              <ArrowLeft className="size-4" />
              Back to task
            </Link>
            <h1 className="text-2xl font-semibold tracking-tight text-neutral-950">THIH Shorts Factory</h1>
            <p className="mt-1 text-sm text-neutral-600">Trim, classify, package, and prepare generated clips for publishing.</p>
          </div>
          <Button type="button" onClick={() => saveTaskSettings()} disabled={isSavingSettings} className="bg-[#d6b25e] text-black hover:bg-[#c7a553]">
            {isSavingSettings ? <Save className="size-4 animate-pulse" /> : <Check className="size-4" />}
            Save AI instructions
          </Button>
        </div>

        {(notice || error) && (
          <Alert className={`mb-5 ${error ? "border-red-200 bg-red-50 text-red-900" : "border-[#d6b25e]/40 bg-[#d6b25e]/10 text-neutral-950"}`}>
            <AlertDescription>{error || notice}</AlertDescription>
          </Alert>
        )}

        <div className="mb-5 flex flex-wrap gap-2">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                type="button"
                onClick={() => setActiveTab(tab.id)}
                className={`inline-flex items-center gap-2 border px-3 py-2 text-sm font-medium transition ${activeTab === tab.id ? "border-black bg-black text-white" : "border-neutral-200 bg-white text-neutral-700 hover:border-neutral-400"}`}
              >
                <Icon className="size-4" />
                {tab.label}
              </button>
            );
          })}
        </div>

        {activeTab === "principles" && <AlgorithmPrinciples />}
        {activeTab === "setup" && <SermonSetup metadata={metadata} onChange={setMetadata} onSaveContentMode={saveTaskSettings} isSaving={isSavingSettings} />}
        {activeTab === "builder" && (
          <ClipBuilder
            taskId={task.id}
            clips={clips}
            selectedClipId={selectedClip?.id ?? null}
            clipStates={clipStates}
            metadata={metadata}
            copiedKey={copiedKey}
            isSavingTrim={isSavingTrim}
            onSelectClip={setSelectedClipId}
            onStateChange={handleStateChange}
            onCopy={handleCopy}
            onSaveTrim={saveTrim}
          />
        )}
        {activeTab === "instructions" && <AIInstructions metadata={metadata} copiedKey={copiedKey} onCopy={handleCopy} />}
      </div>
    </main>
  );
}
