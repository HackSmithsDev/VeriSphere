// aera-web/src/components/common/Loading.jsx
import React from "react";

export default function Loading({ message = "Gathering atmospheric telemetry..." }) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[300px] space-y-4">
      <div 
        className="w-10 h-10 border-3 rounded-full animate-spin"
        style={{
          borderColor: "var(--accent)",
          borderTopColor: "var(--primary)",
        }}
      />
      <p className="text-xs font-medium text-muted-foreground tracking-wide">{message}</p>
    </div>
  );
}