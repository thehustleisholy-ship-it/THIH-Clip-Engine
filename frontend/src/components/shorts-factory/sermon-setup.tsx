import { CONTENT_MODES, type SermonMetadata } from "@/lib/shorts-factory";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";

interface SermonSetupProps {
  metadata: SermonMetadata;
  onChange: (metadata: SermonMetadata) => void;
  onSaveContentMode: () => void;
  isSaving?: boolean;
}

export function SermonSetup({ metadata, onChange, onSaveContentMode, isSaving }: SermonSetupProps) {
  const update = (key: keyof SermonMetadata, value: string) => {
    onChange({ ...metadata, [key]: value });
  };

  return (
    <div className="grid gap-5 lg:grid-cols-[1fr_320px]">
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-2 sm:col-span-2">
          <Label htmlFor="sermon-title">Sermon title</Label>
          <Input id="sermon-title" value={metadata.sermonTitle} onChange={(event) => update("sermonTitle", event.target.value)} />
        </div>
        <div className="space-y-2">
          <Label htmlFor="scripture-reference">Scripture reference</Label>
          <Input id="scripture-reference" value={metadata.scriptureReference} placeholder="Romans 12:2" onChange={(event) => update("scriptureReference", event.target.value)} />
        </div>
        <div className="space-y-2">
          <Label htmlFor="total-duration">Total duration</Label>
          <Input id="total-duration" value={metadata.totalDuration} placeholder="42:18" onChange={(event) => update("totalDuration", event.target.value)} />
        </div>
        <div className="space-y-2 sm:col-span-2">
          <Label htmlFor="core-theme">Core theme</Label>
          <Input id="core-theme" value={metadata.coreTheme} placeholder="Set apart without arrogance" onChange={(event) => update("coreTheme", event.target.value)} />
        </div>
        <div className="space-y-2 sm:col-span-2">
          <Label htmlFor="selection-instructions">Task-level selection instructions</Label>
          <Textarea id="selection-instructions" value={metadata.selectionInstructions} rows={4} placeholder="Prioritize conviction, Scripture clarity, and practical stewardship application." onChange={(event) => update("selectionInstructions", event.target.value)} />
        </div>
      </div>
      <div className="border border-neutral-200 bg-neutral-50 p-4">
        <Label>Content mode</Label>
        <Select value={metadata.contentMode} onValueChange={(value) => update("contentMode", value)}>
          <SelectTrigger className="mt-2 bg-white">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {CONTENT_MODES.map((mode) => (
              <SelectItem key={mode.value} value={mode.value}>{mode.label}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <button type="button" onClick={onSaveContentMode} disabled={isSaving} className="mt-4 w-full bg-black px-4 py-2 text-sm font-medium text-white transition hover:bg-neutral-800 disabled:opacity-50">
          {isSaving ? "Saving" : "Save content mode"}
        </button>
        <p className="mt-3 text-xs leading-5 text-neutral-500">
          Content mode is saved through the existing task settings path and will be used by backend AI analysis when this task is resumed or reprocessed.
        </p>
      </div>
    </div>
  );
}