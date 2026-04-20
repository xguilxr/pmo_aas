"use client";

import type { ReactNode } from "react";

import { ProjectTabsBar } from "@/components/project-tabs-bar";

export function ProjectLayoutClient({
  projectId,
  children,
}: {
  projectId: string;
  children: ReactNode;
}) {
  return (
    <div>
      <ProjectTabsBar projectId={projectId} />
      <div>{children}</div>
    </div>
  );
}
