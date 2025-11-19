import Navigation from '@/components/Navigation';
import StructureNavigator from '@/components/StructureNavigator';

export default function BrowsePage() {
  return (
    <div className="min-h-screen bg-slate-50">
      <Navigation />

      <main className="max-w-5xl mx-auto px-4 py-8">
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-slate-900 mb-2">
            Browse DC Code
          </h1>
          <p className="text-slate-600">
            Navigate through the hierarchical structure of the District of Columbia Code
          </p>
        </div>

        <StructureNavigator />
      </main>
    </div>
  );
}
