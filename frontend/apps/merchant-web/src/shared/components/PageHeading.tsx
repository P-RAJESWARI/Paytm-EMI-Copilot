import type { ReactNode } from 'react';

export interface PageHeadingProps {
  title: string;
  description?: string | undefined;
  /** An optional control on the right, such as a back link or the period switch. */
  action?: ReactNode;
}

// The page title (h1) with its one-line description and an optional action beside it.
export function PageHeading({ title, description, action }: PageHeadingProps) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-4">
      <div className="flex flex-col gap-1">
        <h1 className="text-heading text-navy">{title}</h1>
        {description === undefined ? null : <p className="text-body text-slate">{description}</p>}
      </div>
      {action}
    </div>
  );
}
