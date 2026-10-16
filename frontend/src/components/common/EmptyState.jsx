// aera-web/src/components/common/EmptyState.jsx
import React from "react";
import { CloudOff } from "lucide-react";

export default function EmptyState({
  title = "No Data Found",
  description = "No sensor readings registered yet.",
}) {
  return (
    <div className="flex flex-col items-center justify-center p-8 text-center bg-card border border-border rounded-3xl shadow-xs">
      <div 
        className="w-12 h-12 mb-3.5 rounded-2xl flex items-center justify-center border"
        style={{
          backgroundColor: "var(--accent)",
          borderColor: "var(--primary-light)",
          color: "var(--primary)",
        }}
      >
        <CloudOff className="w-6 h-6" />
      </div>
      <h3 className="text-base font-semibold text-foreground">{title}</h3>
      <p className="text-xs text-muted-foreground max-w-sm mt-1 leading-relaxed">
        {description}
      </p>
    </div>
  );
}