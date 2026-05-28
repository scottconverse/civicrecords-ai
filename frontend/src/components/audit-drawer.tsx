import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

interface AuditDrawerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function AuditDrawer({ open, onOpenChange }: AuditDrawerProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        aria-label="Audit drawer"
        className="right-0 left-auto top-0 h-screen max-w-md translate-x-0 translate-y-0 rounded-none border-l sm:max-w-md"
      >
        <DialogHeader>
          <DialogTitle>Audit drawer</DialogTitle>
          <DialogDescription>
            Recent operator actions and compliance events are available from the audit log.
          </DialogDescription>
        </DialogHeader>
        <div className="rounded-md border bg-muted/40 p-3 text-sm text-muted-foreground">
          No audit events are loaded in this prototype shell.
        </div>
      </DialogContent>
    </Dialog>
  );
}
