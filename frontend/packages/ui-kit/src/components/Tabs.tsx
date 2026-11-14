import { useId, useRef, type KeyboardEvent, type ReactNode } from 'react';

export interface TabDefinition<TabId extends string> {
  id: TabId;
  label: string;
  panel: ReactNode;
}

export interface TabsProps<TabId extends string> {
  /** Names the tab list for screen readers, for example "Report sections". */
  accessibleLabel: string;
  tabs: readonly TabDefinition<TabId>[];
  selectedTabId: TabId;
  onSelectTab: (tabId: TabId) => void;
}

const KEY_TO_INDEX_STEP: Partial<Record<string, number>> = { ArrowRight: 1, ArrowLeft: -1 };

// An accessible tab list (WAI-ARIA tabs pattern): arrow keys, Home and End move and select a tab.
export function Tabs<TabId extends string>({
  accessibleLabel,
  tabs,
  selectedTabId,
  onSelectTab,
}: TabsProps<TabId>) {
  const idPrefix = useId();
  const tabButtons = useRef(new Map<TabId, HTMLButtonElement>());
  const selectedIndex = Math.max(
    0,
    tabs.findIndex((tab) => tab.id === selectedTabId),
  );
  const selectedTab = tabs[selectedIndex];

  // Moves the selection with the keyboard and keeps focus on the newly selected tab.
  function handleTabKeyDown(event: KeyboardEvent<HTMLButtonElement>) {
    const step = KEY_TO_INDEX_STEP[event.key];
    let targetIndex: number | undefined;
    if (step !== undefined) targetIndex = (selectedIndex + step + tabs.length) % tabs.length;
    if (event.key === 'Home') targetIndex = 0;
    if (event.key === 'End') targetIndex = tabs.length - 1;
    const targetTab = targetIndex === undefined ? undefined : tabs[targetIndex];
    if (targetTab === undefined) return;
    event.preventDefault();
    onSelectTab(targetTab.id);
    tabButtons.current.get(targetTab.id)?.focus();
  }

  return (
    <div className="flex flex-col gap-4">
      <div role="tablist" aria-label={accessibleLabel} className="flex gap-2">
        {tabs.map((tab) => {
          const isSelected = tab.id === selectedTab?.id;
          return (
            <button
              key={tab.id}
              ref={(element) => {
                if (element === null) tabButtons.current.delete(tab.id);
                else tabButtons.current.set(tab.id, element);
              }}
              type="button"
              role="tab"
              id={`${idPrefix}-tab-${tab.id}`}
              aria-selected={isSelected}
              aria-controls={`${idPrefix}-panel-${tab.id}`}
              tabIndex={isSelected ? 0 : -1}
              onClick={() => {
                onSelectTab(tab.id);
              }}
              onKeyDown={handleTabKeyDown}
              className={`min-h-touch-target rounded-input px-4 text-body font-semibold ${
                isSelected ? 'bg-navy text-white' : 'bg-white text-navy'
              }`}
            >
              {tab.label}
            </button>
          );
        })}
      </div>
      {selectedTab === undefined ? null : (
        <div
          role="tabpanel"
          id={`${idPrefix}-panel-${selectedTab.id}`}
          aria-labelledby={`${idPrefix}-tab-${selectedTab.id}`}
          tabIndex={0}
        >
          {selectedTab.panel}
        </div>
      )}
    </div>
  );
}
