export function ProfilePage() {
  return (
    <div className="page profile-page">
      <h1>Profile</h1>
      <p className="page-intro">Demo build, synthetic data.</p>
      <section className="card">
        <h2>Demo user</h2>
        <p>Display name: <strong>Demo user</strong></p>
        <p className="note">
          No real account exists. Authentication is not part of this demonstration.
        </p>
      </section>
    </div>
  );
}