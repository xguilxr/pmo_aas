import type { ReactNode } from "react";

import { ProjectLayoutClient } from "@/components/project-layout-client";

export default async function ProjectDetailLayout(props: {
  children: ReactNode;
  params: Promise<{ id: string }>;
}) {
  const { id } = await props.params;
  return <ProjectLayoutClient projectId={id}>{props.children}</ProjectLayoutClient>;
}
