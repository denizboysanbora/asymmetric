import EditorHeader from "@/components/EditorHeader";
import PromptPanel from "@/components/PromptPanel";
import OutputPanel from "@/components/OutputPanel";
import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from "@/components/ui/resizable";

const Index = () => {
  return (
    <div className="h-screen flex flex-col bg-background">
      <EditorHeader />
      
      {/* Desktop: horizontal layout, Mobile: vertical layout */}
      <div className="flex-1 flex flex-col md:hidden">
        <div className="flex-1 border-b border-editor-border">
          <OutputPanel />
        </div>
        <div className="h-[40vh]">
          <PromptPanel />
        </div>
      </div>

      <div className="hidden md:flex flex-1">
        <ResizablePanelGroup direction="horizontal" className="flex-1">
          <ResizablePanel defaultSize={40} minSize={30}>
            <PromptPanel />
          </ResizablePanel>
          
          <ResizableHandle className="w-px bg-editor-border hover:bg-muted-foreground transition-colors" />
          
          <ResizablePanel defaultSize={60} minSize={30}>
            <OutputPanel />
          </ResizablePanel>
        </ResizablePanelGroup>
      </div>
    </div>
  );
};

export default Index;
