export function HelpPage() {
  return (
    <div className="page help-page">
      <h1>Help</h1>
      <p className="page-intro">How this demonstration works.</p>
      <section className="card">
        <h2>What it shows</h2>
        <p>
          Upload a document, see the reading of its fields, compare them against the synthetic demo
          registry, review when asked, and view the on-chain record of the outcome.
        </p>
        <h2>Is this a government service?</h2>
        <p>
          No. This is a demo build with synthetic data. It does not evaluate real documents.
        </p>
      </section>
    </div>
  );
}