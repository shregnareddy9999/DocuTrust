export type PipelineStepId = 'upload' | 'extract' | 'compare' | 'review' | 'record';

const STEPS: PipelineStepId[] = ['upload', 'extract', 'compare', 'review', 'record'];

const LABELS: Record<PipelineStepId, string> = {
  upload: 'Upload',
  extract: 'Extract',
  compare: 'Compare',
  review: 'Review',
  record: 'Record',
};

export function PipelineTrack({ current }: { current: PipelineStepId }) {
  const currentIndex = STEPS.indexOf(current);
  return (
    <div className="pipeline-track" aria-label="Pipeline steps">
      {STEPS.map((id, index) => {
        const className =
          index === currentIndex
            ? 'pipeline-step pipeline-step--active'
            : index < currentIndex
              ? 'pipeline-step pipeline-step--done'
              : 'pipeline-step';
        return (
          <div key={id} className={className}>
            <span className="pipeline-step__dot" aria-hidden="true" />
            <span>
              {index + 1}. {LABELS[id]}
            </span>
          </div>
        );
      })}
    </div>
  );
}