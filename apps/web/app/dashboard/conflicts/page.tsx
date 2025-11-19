import Navigation from "@/components/Navigation";
import AnalysisDashboard from "@/components/AnalysisDashboard";

export default function ConflictsPage() {
  return (
    <>
      <Navigation breadcrumbs={[
        { label: "Home", href: "/" },
        { label: "Dashboard", href: "/dashboard" },
        { label: "Analysis", href: "/dashboard/conflicts" }
      ]} />
      <div className="min-h-screen bg-slate-50 py-8 px-4">
        <div className="max-w-5xl mx-auto">
          <div className="mb-8">
            <h1 className="text-3xl font-bold text-slate-900 mb-2">Legislative Analysis</h1>
            <p className="text-slate-600">
              Potential conflicts and redundancies identified by AI analysis.
              Review these items to ensure legal consistency.
            </p>
          </div>
          
          <AnalysisDashboard />
        </div>
      </div>
    </>
  );
}
