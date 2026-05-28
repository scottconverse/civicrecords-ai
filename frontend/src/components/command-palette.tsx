import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";

interface CommandPaletteProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const commands = ["Search records", "Open requests", "Review audit log"];

export function CommandPalette({ open, onOpenChange }: CommandPaletteProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent aria-label="Command palette" className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Command palette</DialogTitle>
          <DialogDescription>
            Jump to common operator work without leaving the keyboard.
          </DialogDescription>
        </DialogHeader>
        <Input aria-label="Command search" placeholder="Type a command" autoFocus />
        <div className="grid gap-1">
          {commands.map((command) => (
            <button
              key={command}
              type="button"
              className="rounded-md px-3 py-2 text-left text-sm hover:bg-muted focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
            >
              {command}
            </button>
          ))}
        </div>
      </DialogContent>
    </Dialog>
  );
}
