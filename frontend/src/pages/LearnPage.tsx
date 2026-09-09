import Learn from "../components/Learn";

/* The academy as a page of its own, so it is a place in the product and not only something to do while waiting. */
export default function LearnPage() {
  return (
    <main>
      <div className="crumb">VVS-akademin</div>
      <Learn />
    </main>
  );
}
