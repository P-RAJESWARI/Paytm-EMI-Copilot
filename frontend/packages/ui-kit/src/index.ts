// Public API of the ui-kit: presentational components only. Text always arrives through props,
// so each app translates it. Import '@emi-copilot/ui-kit/styles.css' once in the app entry.
export { Button, type ButtonProps } from './components/Button';
export {
  getButtonClassName,
  type ButtonSize,
  type ButtonStyleOptions,
  type ButtonVariant,
} from './components/getButtonClassName';
export {
  Card,
  type CardElement,
  type CardPadding,
  type CardProps,
  type CardSurface,
} from './components/Card';
export { Chip, type ChipProps, type ChipShape, type ChipTone } from './components/Chip';
export { ExpandableCard, type ExpandableCardProps } from './components/ExpandableCard';
export {
  ExpandableCardButton,
  type ExpandableCardButtonProps,
} from './components/ExpandableCardButton';
export {
  ExpandableCardPanel,
  type ExpandableCardPanelProps,
} from './components/ExpandableCardPanel';
export { FunnelBar, type FunnelBarProps, type FunnelBarTone } from './components/FunnelBar';
export {
  LanguageToggle,
  type LanguageToggleOption,
  type LanguageToggleProps,
  type LanguageToggleSurface,
} from './components/LanguageToggle';
export { PinInput, type PinInputProps } from './components/PinInput';
export { QrPanel, type QrPanelLayout, type QrPanelProps } from './components/QrPanel';
export {
  SegmentedControl,
  type SegmentedControlOption,
  type SegmentedControlProps,
} from './components/SegmentedControl';
export { StatusChip, type StatusChipProps } from './components/StatusChip';
export type { StatusChipTone } from './components/statusChipTone';
export { Tabs, type TabDefinition, type TabsProps } from './components/Tabs';
