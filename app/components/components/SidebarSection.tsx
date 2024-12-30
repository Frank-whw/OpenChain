import React from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';

interface SidebarSectionProps {
  title: string;
  items: { id: string; label: string }[];
  activeSection: string;
  scrollToSection: (sectionId: string) => void;
  filterContent: (content: string) => boolean;
}

const SidebarSection: React.FC<SidebarSectionProps> = ({
  title,
  items,
  activeSection,
  scrollToSection,
  filterContent,
}) => {
  const [isExpanded, setIsExpanded] = React.useState(true);

  return (
    <div className="mb-6">
      <div
        className="flex justify-between items-center cursor-pointer"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <h3 className="text-sm font-semibold text-gray-600 uppercase tracking-wider mb-2">
          {title}
        </h3>
        {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
      </div>
      {isExpanded && (
        <div>
          {items.map((item) => (
            filterContent(item.label) && (
              <a
                key={item.id}
                href={`#${item.id}`}
                className={`block py-2 px-4 text-gray-700 hover:bg-gray-100 hover:text-blue-600 rounded ${
                  activeSection === item.id ? 'bg-gray-100 text-blue-600' : ''
                }`}
                onClick={(e) => {
                  e.preventDefault();
                  scrollToSection(item.id);
                }}
              >
                {item.label}
              </a>
            )
          ))}
        </div>
      )}
    </div>
  );
};

export default SidebarSection;

