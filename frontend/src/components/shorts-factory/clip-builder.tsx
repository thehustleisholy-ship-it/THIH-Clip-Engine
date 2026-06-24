import { Save, Scissors } from "lucide-react";

import { AVOIDANCE_CHECKLIST, MOMENT_TYPES, formatSeconds, getDurationSeconds, parseTimeToSeconds, validateDuration, type ClipFactoryState, type FactoryClip, type MomentType, type SermonMetadata } from "@/lib/shorts-factory";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import DynamicVideoPlayer from "@/components/dynamic-video-player";
import { TrimControls } from "./trim-controls";
import { CaptionPacket } from "./caption-packet";

interface ClipBuilderProps {
  taskId: string;
  clips: FactoryClip[];
  selectedClipId: string | null;
  clipStates: Record<string, ClipFactoryState>;
  metadata: SermonMetadata;
  copiedKey: string | null;
  isSavingTrim: boolean;
  onSelectClip: (clipId: string) => void;
  onStateChange: (clipId: string, state: ClipFactoryState) => void;
  onCopy: (key: string, value: string) => void;
  onSaveTrim: (clip: FactoryClip, state: ClipFactoryState) => Promise<void>;
}

function getClipUrl(videoUrl: string) {
  return videoUrl.startsWith("/api/") ? videoUrl : `/api${videoUrl}`;
}

export function ClipBuilder({ taskId, clips, selectedClipId, clipStates, metadata, copiedKey, isSavingTrim, onSelectClip, onStateChange, onCopy, onSaveTrim }: ClipBuilderProps) {
  const selectedClip = clips.find((clip) => clip.id === selectedClipId) || clips[0];
  const selectedState = selectedClip ? clipStates[selectedClip.id] : null;
  const duration = selectedState ? getDurationSeconds(selectedState.startTime, selectedState.endTime) : null;
  const trimError = selectedState ? validateDuration(selectedState.startTime, selectedState.endTime, selectedState.durationMode) : null;

  if (!selectedClip || !selectedState) {
    return <div className="border border-neutral-200 bg-white p-6 text-sm text-neutral-600">No generated clips are available for this task yet.</div>;
  }

  const sourceStart = parseTimeToSeconds(selectedClip.start_time) ?? 0;
  const sourceEnd = parseTimeToSeconds(selectedClip.end_time) ?? sourceStart + selectedClip.duration;
  const requestedStart = parseTimeToSeconds(selectedState.startTime);
  const requestedEnd = parseTimeToSeconds(selectedState.endTime);
  const isWithinClip = requestedStart !== null && requestedEnd !== null && requestedStart >= sourceStart && requestedEnd <= sourceEnd;

  return (
    <div className="grid gap-5 xl:grid-cols-[280px_1fr_360px]">
      <div className="border border-neutral-200 bg-white">
        <div className="border-b border-neutral-200 p-4">
          <h3 className="text-sm font-semibold text-neutral-950">Generated clips</h3>
          <p className="mt-1 text-xs text-neutral-500">Task {taskId}</p>
        </div>
        <div className="max-h-[640px] overflow-y-auto p-2">
          {clips.map((clip) => (
            <button key={clip.id} type="button" onClick={() => onSelectClip(clip.id)} className={`mb-2 w-full border p-3 text-left transition ${clip.id === selectedClip.id ? "border-[#d6b25e] bg-[#d6b25e]/10" : "border-neutral-200 bg-white hover:bg-neutral-50"}`}>
              <div className="flex items-center justify-between gap-2">
                <span className="text-sm font-semibold text-neutral-950">Clip {clip.clip_order}</span>
                <span className="text-xs text-neutral-500">{clip.start_time} - {clip.end_time}</span>
              </div>
              <p className="mt-2 line-clamp-2 text-xs leading-5 text-neutral-600">{clip.text}</p>
            </button>
          ))}
        </div>
      </div>

      <div className="space-y-5">
        <div className="border border-neutral-200 bg-white p-4">
          <DynamicVideoPlayer src={getClipUrl(selectedClip.video_url)} poster="/placeholder-video.jpg" />
        </div>
        <div className="border border-neutral-200 bg-white p-5">
          <div className="mb-4 flex flex-wrap items-center gap-2">
            <Badge className="bg-black text-white">THIH {selectedClip.thih_score ?? 0}</Badge>
            {typeof selectedClip.thih?.canon_fit === "number" && <Badge variant="outline">Canon {selectedClip.thih.canon_fit}</Badge>}
            {typeof selectedClip.thih?.stewardship_usefulness === "number" && <Badge variant="outline">Stewardship {selectedClip.thih.stewardship_usefulness}</Badge>}
            {selectedClip.platform_fit?.map((platform) => <Badge key={platform} variant="outline">{platform}</Badge>)}
          </div>
          <div className="grid gap-5 lg:grid-cols-2">
            <div className="space-y-4">
              <div className="space-y-2">
                <Label>Moment type</Label>
                <Select value={selectedState.momentType} onValueChange={(value) => onStateChange(selectedClip.id, { ...selectedState, momentType: value as MomentType })}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {MOMENT_TYPES.map((type) => <SelectItem key={type} value={type}>{type}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <TrimControls state={selectedState} onChange={(state) => onStateChange(selectedClip.id, state)} />
              {!isWithinClip && <p className="text-sm text-amber-700">Trim range must stay inside the current rendered clip: {selectedClip.start_time} - {selectedClip.end_time}.</p>}
              <Button type="button" disabled={Boolean(trimError) || !isWithinClip || isSavingTrim} onClick={() => onSaveTrim(selectedClip, selectedState)} className="bg-black text-white hover:bg-neutral-800">
                <Save className="size-4" />
                {isSavingTrim ? "Saving trim" : "Save trim metadata"}
              </Button>
            </div>
            <div className="space-y-3">
              <div className="flex items-center gap-2 text-sm font-semibold text-neutral-950">
                <Scissors className="size-4 text-[#d6b25e]" />
                Avoidance checklist
              </div>
              {AVOIDANCE_CHECKLIST.map((item) => (
                <label key={item} className="flex items-start gap-3 text-sm text-neutral-700">
                  <Checkbox checked={Boolean(selectedState.checklist[item])} onCheckedChange={(checked) => onStateChange(selectedClip.id, { ...selectedState, checklist: { ...selectedState.checklist, [item]: Boolean(checked) } })} />
                  <span>{item}</span>
                </label>
              ))}
              <div className="border border-neutral-200 bg-neutral-50 p-3 text-sm text-neutral-600">
                Current factory duration: <strong className="text-neutral-950">{duration === null ? "Invalid" : formatSeconds(duration)}</strong>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="border border-neutral-200 bg-white p-5">
        <CaptionPacket clip={selectedClip} state={selectedState} metadata={metadata} copiedKey={copiedKey} onChange={(state) => onStateChange(selectedClip.id, state)} onCopy={onCopy} />
      </div>
    </div>
  );
}