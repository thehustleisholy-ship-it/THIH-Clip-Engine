import { Clipboard, Check } from "lucide-react";

import { buildCaptionPacket, getTitleOptions, type ClipFactoryState, type FactoryClip, type SermonMetadata } from "@/lib/shorts-factory";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";

interface CaptionPacketProps {
  clip: FactoryClip;
  state: ClipFactoryState;
  metadata: SermonMetadata;
  copiedKey: string | null;
  onChange: (state: ClipFactoryState) => void;
  onCopy: (key: string, value: string) => void;
}

export function CaptionPacket({ clip, state, metadata, copiedKey, onChange, onCopy }: CaptionPacketProps) {
  const titleOptions = getTitleOptions(clip, metadata, state.momentType);
  const packet = buildCaptionPacket(clip, state, metadata);
  const hashtags = state.hashtags;

  const CopyIcon = ({ active }: { active: boolean }) => active ? <Check className="size-4" /> : <Clipboard className="size-4" />;

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <Label>Title options</Label>
        <Select value={state.selectedTitle} onValueChange={(value) => onChange({ ...state, selectedTitle: value })}>
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {titleOptions.map((title) => (
              <SelectItem key={title} value={title}>{title}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Button type="button" variant="outline" size="sm" onClick={() => onCopy("title", state.selectedTitle)}>
          <CopyIcon active={copiedKey === "title"} />
          Copy title
        </Button>
      </div>
      <div className="space-y-2">
        <Label>CTA</Label>
        <Textarea value={state.cta} rows={2} onChange={(event) => onChange({ ...state, cta: event.target.value })} />
        <Button type="button" variant="outline" size="sm" onClick={() => onCopy("cta", state.cta)}>
          <CopyIcon active={copiedKey === "cta"} />
          Copy CTA
        </Button>
      </div>
      <div className="space-y-2">
        <Label>Hashtags</Label>
        <Textarea value={hashtags} rows={2} onChange={(event) => onChange({ ...state, hashtags: event.target.value })} />
        <Button type="button" variant="outline" size="sm" onClick={() => onCopy("hashtags", hashtags)}>
          <CopyIcon active={copiedKey === "hashtags"} />
          Copy hashtags
        </Button>
      </div>
      <div className="space-y-2">
        <Label>Full platform packet</Label>
        <pre className="whitespace-pre-wrap border border-neutral-200 bg-neutral-950 p-4 text-xs leading-5 text-neutral-100">{packet}</pre>
        <div className="flex flex-wrap gap-2">
          <Button type="button" variant="outline" size="sm" onClick={() => onCopy("caption", clip.recommended_caption || metadata.coreTheme || clip.text)}>
            <CopyIcon active={copiedKey === "caption"} />
            Copy caption
          </Button>
          <Button type="button" size="sm" className="bg-[#d6b25e] text-black hover:bg-[#c7a351]" onClick={() => onCopy("packet", packet)}>
            <CopyIcon active={copiedKey === "packet"} />
            Copy full packet
          </Button>
        </div>
      </div>
    </div>
  );
}