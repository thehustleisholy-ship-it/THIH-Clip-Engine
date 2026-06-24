import { AlertCircle } from "lucide-react";

import { DURATION_MODES, formatSeconds, getDurationSeconds, validateDuration, type ClipFactoryState } from "@/lib/shorts-factory";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

interface TrimControlsProps {
  state: ClipFactoryState;
  onChange: (state: ClipFactoryState) => void;
}

export function TrimControls({ state, onChange }: TrimControlsProps) {
  const duration = getDurationSeconds(state.startTime, state.endTime);
  const error = validateDuration(state.startTime, state.endTime, state.durationMode);

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-2">
          <Label htmlFor="clip-start-time">Start Time</Label>
          <Input id="clip-start-time" value={state.startTime} placeholder="0:08" onChange={(event) => onChange({ ...state, startTime: event.target.value })} />
        </div>
        <div className="space-y-2">
          <Label htmlFor="clip-end-time">End Time</Label>
          <Input id="clip-end-time" value={state.endTime} placeholder="0:37" onChange={(event) => onChange({ ...state, endTime: event.target.value })} />
        </div>
      </div>
      <div className="grid gap-3 sm:grid-cols-[1fr_auto] sm:items-end">
        <div className="space-y-2">
          <Label>Duration mode</Label>
          <Select value={state.durationMode} onValueChange={(value) => onChange({ ...state, durationMode: value as ClipFactoryState["durationMode"] })}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {DURATION_MODES.map((mode) => (
                <SelectItem key={mode} value={mode}>{mode}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="border border-[#d6b25e]/50 bg-[#d6b25e]/10 px-3 py-2 text-sm font-semibold text-neutral-950">
          {duration === null ? "Invalid" : formatSeconds(duration)}
        </div>
      </div>
      {error && (
        <p className="flex items-center gap-2 text-sm text-red-700">
          <AlertCircle className="size-4" />
          {error}
        </p>
      )}
    </div>
  );
}