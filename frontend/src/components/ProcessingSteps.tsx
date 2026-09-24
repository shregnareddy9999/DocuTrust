export type ProcessingStepState = 'done' | 'active' | 'pending';

export interface ProcessingStep {
  label: string;
  state: ProcessingStepState;
}

const MARK: Record<ProcessingStepState, string> = {
  done: '✓',
  active: '●',
  pending: '○',
};

interface ProcessingStepsProps {
  steps: ProcessingStep[];
}

export function ProcessingSteps({ steps }: ProcessingStepsProps) {
  return (
    <ol className="processing-steps" aria-label="Processing steps" role="status">
      {steps.map((step) => (
        <li
          key={step.label}
          className={`processing-step processing-step--${step.state}`}
          data-state={step.state}
        >
          <span className="processing-step__mark" aria-hidden="true">
            {MARK[step.state]}
          </span>
          <span className="processing-step__label">{step.label}</span>
          {step.state === 'active' ? (
            <span className="visually-hidden">in progress</span>
          ) : null}
        </li>
      ))}
    </ol>
  );
}