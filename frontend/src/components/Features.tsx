import {
  FileStack,
  Cpu,
  Target,
  Clock,
} from 'lucide-react';

export default function Features() {
  const currentFeatures = [
    {
      icon: FileStack,
      title: 'Multi-Format Support',
      description: 'Process PDF, PPT, Word documents, images, and direct text input seamlessly',
      gradient: 'from-indigo-500 to-indigo-600',
    },
    {
      icon: Cpu,
      title: 'AI-Powered Summarization',
      description: 'Advanced transformer-based NLP models for intelligent content analysis',
      gradient: 'from-violet-500 to-violet-600',
    },
    {
      icon: Target,
      title: 'Academic-Focused Output',
      description: 'Tailored summaries maintaining clarity, structure, and key concepts',
      gradient: 'from-fuchsia-500 to-fuchsia-600',
    },
    {
      icon: Clock,
      title: 'Time-Saving Learning',
      description: 'Reduce reading time significantly while retaining important information',
      gradient: 'from-purple-500 to-purple-600',
    },
  ];



  return (
    <section className="py-16 px-6 bg-white">
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-12">
          <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4">
            Powerful Features
          </h2>
          <p className="text-gray-600 max-w-2xl mx-auto">
            Everything you need to transform your academic learning experience
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-16">
          {currentFeatures.map((feature, index) => {
            const Icon = feature.icon;
            return (
              <div
                key={index}
                className="bg-white rounded-xl p-6 border-2 border-gray-100 hover:border-indigo-100 hover:shadow-xl hover:shadow-indigo-100/50 transition-all duration-300 group"
              >
                <div
                  className={`w-14 h-14 rounded-lg bg-gradient-to-br ${feature.gradient} flex items-center justify-center mb-4 group-hover:scale-110 transition-transform duration-300 shadow-lg`}
                >
                  <Icon className="w-7 h-7 text-white" />
                </div>
                <h3 className="text-lg font-bold text-gray-900 mb-2">
                  {feature.title}
                </h3>
                <p className="text-sm text-gray-600 leading-relaxed">
                  {feature.description}
                </p>
              </div>
            );
          })}
        </div>


      </div>
    </section>
  );
}