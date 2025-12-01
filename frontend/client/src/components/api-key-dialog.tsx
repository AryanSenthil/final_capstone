import { useState, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Eye, EyeOff, Key, Loader2 } from "lucide-react";
import { useToast } from "@/hooks/use-toast";

interface ApiKeyDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

interface ApiKeyStatus {
  configured: boolean;
  masked_key: string | null;
}

export function ApiKeyDialog({ open, onOpenChange }: ApiKeyDialogProps) {
  const [apiKey, setApiKey] = useState("");
  const [showKey, setShowKey] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [existingKeyMasked, setExistingKeyMasked] = useState<string | null>(null);
  const { toast } = useToast();

  // Load existing API key status when dialog opens
  useEffect(() => {
    if (open) {
      loadApiKeyStatus();
    }
  }, [open]);

  const loadApiKeyStatus = async () => {
    setIsLoading(true);
    try {
      const response = await fetch("/api/settings/api-key");
      if (response.ok) {
        const data: ApiKeyStatus = await response.json();
        if (data.configured && data.masked_key) {
          setExistingKeyMasked(data.masked_key);
          setApiKey(""); // Clear input, user can type new key to replace
        } else {
          setExistingKeyMasked(null);
        }
      }
    } catch (error) {
      console.error("Failed to load API key status:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSave = async () => {
    if (!apiKey.trim()) {
      toast({
        title: "API Key Required",
        description: "Please enter your OpenAI API key",
        variant: "destructive",
      });
      return;
    }

    setIsSaving(true);
    try {
      // Send to backend to save to .env file
      const response = await fetch("/api/settings/api-key", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ api_key: apiKey }),
      });

      if (!response.ok) throw new Error("Failed to save API key");

      toast({
        title: "API Key Saved",
        description: "Your OpenAI API key has been saved to .env file successfully",
      });

      onOpenChange(false);
      setApiKey("");
      setExistingKeyMasked(null);
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to save API key. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[650px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Key className="h-5 w-5 text-primary" />
            OpenAI API Key Configuration
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : (
            <>
              {existingKeyMasked && (
                <div className="rounded-lg border border-border bg-muted/30 p-4 space-y-2">
                  <p className="text-sm font-medium text-foreground">Current API Key</p>
                  <p className="text-sm font-mono text-muted-foreground">{existingKeyMasked}</p>
                  <p className="text-xs text-muted-foreground">
                    Enter a new key below to replace the existing one.
                  </p>
                </div>
              )}

              <div className="space-y-2">
                <Label htmlFor="api-key">{existingKeyMasked ? "New API Key" : "API Key"}</Label>
                <div className="relative">
                  <Input
                    id="api-key"
                    type={showKey ? "text" : "password"}
                    value={apiKey}
                    onChange={(e) => setApiKey(e.target.value)}
                    placeholder="sk-..."
                    className="pr-10"
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="absolute right-0 top-0 h-full px-3 hover:bg-transparent"
                    onClick={() => setShowKey(!showKey)}
                  >
                    {showKey ? (
                      <EyeOff className="h-4 w-4 text-muted-foreground" />
                    ) : (
                      <Eye className="h-4 w-4 text-muted-foreground" />
                    )}
                  </Button>
                </div>
              </div>
            </>
          )}

          <div className="rounded-lg border border-border bg-muted/50 p-4 space-y-2">
            <p className="text-sm font-medium">Where to get an API key:</p>
            <ol className="text-xs text-muted-foreground space-y-1 list-decimal list-inside">
              <li>Visit <a href="https://platform.openai.com/api-keys" target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">platform.openai.com/api-keys</a></li>
              <li>Sign in or create an OpenAI account</li>
              <li>Click "Create new secret key"</li>
              <li>Copy the key and paste it above</li>
            </ol>
          </div>
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => {
              onOpenChange(false);
              setApiKey("");
            }}
            className="hover:shadow-md hover:scale-105 active:scale-95 transition-all duration-200"
          >
            Cancel
          </Button>
          <Button
            onClick={handleSave}
            disabled={isSaving || !apiKey.trim()}
            className="hover:shadow-md hover:scale-105 active:scale-95 transition-all duration-200"
          >
            {isSaving ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Saving...
              </>
            ) : (
              "Save API Key"
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
