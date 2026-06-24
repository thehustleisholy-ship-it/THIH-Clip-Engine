"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, AlertCircle } from "lucide-react";

import { ShortsFactory } from "@/components/shorts-factory/shorts-factory";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import type { FactoryClip } from "@/lib/shorts-factory";

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

export default function ShortsFactoryTaskPage() {
  const params = useParams<{ id: string }>();
  const [task, setTask] = useState<FactoryTask | null>(null);
  const [clips, setClips] = useState<FactoryClip[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadFactoryData = useCallback(async () => {
    if (!params.id) return;
    setError(null);
    const taskResponse = await fetch(`/api/tasks/${params.id}`, { cache: "no-store" });
    if (!taskResponse.ok) throw new Error(await parseError(taskResponse));
    const taskData = await taskResponse.json();

    const clipsResponse = await fetch(`/api/tasks/${params.id}/clips`, { cache: "no-store" });
    if (!clipsResponse.ok) throw new Error(await parseError(clipsResponse));
    const clipsData = await clipsResponse.json();

    setTask(taskData);
    setClips((clipsData.clips || []).sort((a: FactoryClip, b: FactoryClip) => (a.clip_order ?? 0) - (b.clip_order ?? 0)));
  }, [params.id]);

  useEffect(() => {
    let cancelled = false;
    setIsLoading(true);
    loadFactoryData()
      .catch((loadError) => {
        if (!cancelled) setError(loadError instanceof Error ? loadError.message : "Unable to load Shorts Factory.");
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [loadFactoryData]);

  if (isLoading) {
    return (
      <main className="min-h-screen bg-neutral-50 px-4 py-8">
        <div className="mx-auto max-w-7xl space-y-4">
          <Skeleton className="h-10 w-72" />
          <Skeleton className="h-14 w-full" />
          <Skeleton className="h-[560px] w-full" />
        </div>
      </main>
    );
  }

  if (error || !task) {
    return (
      <main className="min-h-screen bg-neutral-50 px-4 py-8">
        <div className="mx-auto max-w-3xl space-y-4">
          <Link href={`/tasks/${params.id}`} className="inline-flex items-center gap-2 text-sm text-neutral-600 hover:text-neutral-950">
            <ArrowLeft className="size-4" />
            Back to task
          </Link>
          <Alert className="border-red-200 bg-red-50 text-red-900">
            <AlertCircle className="size-4" />
            <AlertDescription>{error || "Task not found."}</AlertDescription>
          </Alert>
        </div>
      </main>
    );
  }

  if (clips.length === 0) {
    return (
      <main className="min-h-screen bg-neutral-50 px-4 py-8">
        <div className="mx-auto max-w-3xl space-y-4">
          <Link href={`/tasks/${task.id}`} className="inline-flex items-center gap-2 text-sm text-neutral-600 hover:text-neutral-950">
            <ArrowLeft className="size-4" />
            Back to task
          </Link>
          <Alert>
            <AlertDescription>Shorts Factory opens after this task has generated at least one clip.</AlertDescription>
          </Alert>
          <Button asChild variant="outline">
            <Link href={`/tasks/${task.id}`}>View task</Link>
          </Button>
        </div>
      </main>
    );
  }

  return <ShortsFactory task={task} clips={clips} onRefresh={loadFactoryData} />;
}
