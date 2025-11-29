import { Switch, Route } from "wouter";
import { QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "next-themes";
import { queryClient } from "./lib/queryClient";
import { Toaster } from "@/components/ui/toaster";
import Layout from "@/components/layout";
import DatabasePage from "@/pages/database";
import RawDatabasePage from "@/pages/raw-database";
import LabelDetailView from "@/pages/label-detail";
import TrainingPage from "@/pages/training";
import ModelsPage from "@/pages/models";
import ModelDetailPage from "@/pages/model-detail";
import ReportsPage from "@/pages/reports";
import NotFound from "@/pages/not-found";

function Router() {
  return (
    <Layout>
      <Switch>
        <Route path="/" component={DatabasePage} />
        <Route path="/raw" component={RawDatabasePage} />
        <Route path="/database/:id" component={LabelDetailView} />
        <Route path="/training" component={TrainingPage} />
        <Route path="/models" component={ModelsPage} />
        <Route path="/models/:id" component={ModelDetailPage} />
        <Route path="/reports" component={ReportsPage} />
        <Route component={NotFound} />
      </Switch>
    </Layout>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider attribute="class" defaultTheme="dark" enableSystem={false}>
        <Toaster />
        <Router />
      </ThemeProvider>
    </QueryClientProvider>
  );
}

export default App;
