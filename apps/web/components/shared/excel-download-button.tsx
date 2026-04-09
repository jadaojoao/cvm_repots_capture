"use client";

import { DownloadIcon } from "lucide-react";
import type { ComponentProps } from "react";
import { useState } from "react";

import { getUserFacingErrorMessage } from "@/lib/api";
import { downloadFile } from "@/lib/download-file";
import { track, type TrackEventName } from "@/lib/track";
import { Button } from "@/components/ui/button";

type ExcelDownloadButtonProps = {
  endpoint: string;
  fallbackFilename: string;
  buttonLabel: string;
  pendingLabel: string;
  trackingEvent: TrackEventName;
  failureTrackingEvent: TrackEventName;
  trackingPayload?: Record<string, string | number | boolean>;
  disabled?: boolean;
  className?: string;
  variant?: ComponentProps<typeof Button>["variant"];
  size?: ComponentProps<typeof Button>["size"];
};

export function ExcelDownloadButton({
  endpoint,
  fallbackFilename,
  buttonLabel,
  pendingLabel,
  trackingEvent,
  failureTrackingEvent,
  trackingPayload,
  disabled = false,
  className,
  variant = "default",
  size = "lg",
}: ExcelDownloadButtonProps) {
  const [pending, setPending] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  async function handleDownload() {
    if (disabled || pending) {
      return;
    }

    setPending(true);
    setErrorMessage(null);

    try {
      const filename = await downloadFile(endpoint, fallbackFilename);
      track(trackingEvent, {
        ...(trackingPayload ?? {}),
        file_name: filename,
      });
    } catch (error) {
      const message = getUserFacingErrorMessage(error);
      setErrorMessage(message);
      track(failureTrackingEvent, {
        ...(trackingPayload ?? {}),
        error_message: message,
      });
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="space-y-1.5">
      <Button
        type="button"
        variant={variant}
        size={size}
        className={className}
        onClick={handleDownload}
        disabled={disabled || pending}
      >
        <DownloadIcon className="size-4" />
        {pending ? pendingLabel : buttonLabel}
      </Button>
      {errorMessage ? (
        <p className="max-w-64 text-xs leading-5 text-destructive">
          {errorMessage}
        </p>
      ) : null}
    </div>
  );
}
