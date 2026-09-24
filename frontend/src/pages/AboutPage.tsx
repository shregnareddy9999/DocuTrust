export function AboutPage() {
  return (
    <div className="page about-page">
      <h1>About</h1>
      <p className="page-intro">About this demonstration build.</p>
      <section className="card">
        <h2>DocuTrust</h2>
        <p>
          A demonstration that compares a document's extracted fields against a synthetic demo
          registry and records the verification outcome on a blockchain.
        </p>
        <p className="note">Demo build, synthetic data.</p>
      </section>
    </div>
  );
}