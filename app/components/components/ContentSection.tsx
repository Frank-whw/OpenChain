import React from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';

interface ContentSectionProps {
  id: string;
  title: string;
  children: React.ReactNode;
  expanded: boolean;
  toggleSection: () => void;
  filterContent: (content: string) => boolean;
}

const ContentSection: React.FC<ContentSectionProps> = ({
  id,
  title,
  children,
  expanded,
  toggleSection,
  filterContent,
}) => {
  if (!filterContent(title)) {
    return null;
  }

  return (
    <section id={id} className="mb-12">
      <div
        className="flex justify-between items-center cursor-pointer"
        onClick={toggleSection}
      >
        <h2 className="text-3xl font-bold mb-6 pb-2 border-b-2 border-blue-500">
          {title}
        </h2>
        {expanded ? <ChevronUp size={24} /> : <ChevronDown size={24} />}
      </div>
      {expanded && <div>{children}</div>}
    </section>
  );
};

export default ContentSection;

