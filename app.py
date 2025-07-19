import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from urllib.parse import urlparse
import time

# Page configuration
st.set_page_config(
    page_title="🔍 Accessibility Analyzer",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

class AccessibilityAnalyzer:
    def __init__(self, url, html_content):
        self.url = url
        self.soup = BeautifulSoup(html_content, 'html.parser')
        self.issues = []
    
    def analyze(self):
        """Run all accessibility checks"""
        self.check_images()
        self.check_headings()
        self.check_form_labels()
        self.check_clickable_elements()
        self.check_color_contrast()
        self.check_links()
        self.check_tables()
        return self.issues
    
    def check_images(self):
        """Check for missing alt text on images"""
        images = self.soup.find_all('img')
        for i, img in enumerate(images):
            src = img.get('src', f'Image #{i+1}')
            alt = img.get('alt')
            
            if alt is None:
                self.issues.append({
                    'type': 'Missing Alt Text',
                    'severity': 'High',
                    'element': f'<img src="{src[:50]}...">',
                    'description': 'Image missing alt attribute',
                    'impact': 'Screen readers cannot describe this image to users',
                    'solution': 'Add descriptive alt text or alt="" for decorative images',
                    'location': f'Image {i+1}'
                })
            elif alt.strip() == '':
                self.issues.append({
                    'type': 'Empty Alt Text',
                    'severity': 'Low',
                    'element': f'<img src="{src[:50]}..." alt="">',
                    'description': 'Image has empty alt attribute',
                    'impact': 'Marked as decorative - ensure this is intentional',
                    'solution': 'Verify if image is truly decorative or needs description',
                    'location': f'Image {i+1}'
                })
    
    def check_headings(self):
        """Check heading structure"""
        headings = self.soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        
        if not headings:
            self.issues.append({
                'type': 'No Headings',
                'severity': 'High',
                'element': 'Document',
                'description': 'No heading elements found',
                'impact': 'Users cannot navigate page structure with assistive technology',
                'solution': 'Add proper heading hierarchy starting with h1',
                'location': 'Entire document'
            })
            return
        
        h1_count = len(self.soup.find_all('h1'))
        if h1_count == 0:
            self.issues.append({
                'type': 'Missing H1',
                'severity': 'High',
                'element': 'Document',
                'description': 'No h1 element found',
                'impact': 'Page lacks main heading for screen readers',
                'solution': 'Add one h1 element as the main page heading',
                'location': 'Document head'
            })
        elif h1_count > 1:
            self.issues.append({
                'type': 'Multiple H1',
                'severity': 'Medium',
                'element': 'Document',
                'description': f'Found {h1_count} h1 elements',
                'impact': 'Multiple main headings can confuse navigation',
                'solution': 'Use only one h1 per page',
                'location': 'Multiple locations'
            })
        
        # Check for heading level skips
        prev_level = 0
        for i, heading in enumerate(headings):
            current_level = int(heading.name[1])
            if prev_level > 0 and current_level > prev_level + 1:
                self.issues.append({
                    'type': 'Heading Level Skip',
                    'severity': 'Medium',
                    'element': f'<{heading.name}>{heading.get_text()[:30]}...</{heading.name}>',
                    'description': f'Heading jumps from h{prev_level} to h{current_level}',
                    'impact': 'Breaks logical heading hierarchy',
                    'solution': 'Use sequential heading levels (h1, h2, h3, etc.)',
                    'location': f'Heading {i+1}'
                })
            prev_level = current_level
    
    def check_form_labels(self):
        """Check for unlabeled form inputs"""
        inputs = self.soup.find_all(['input', 'textarea', 'select'])
        
        for i, input_elem in enumerate(inputs):
            input_type = input_elem.get('type', 'text')
            if input_type in ['hidden', 'submit', 'button']:
                continue
            
            input_id = input_elem.get('id')
            aria_label = input_elem.get('aria-label')
            aria_labelledby = input_elem.get('aria-labelledby')
            
            # Check for associated label
            has_label = False
            if input_id:
                label = self.soup.find('label', {'for': input_id})
                if label:
                    has_label = True
            
            # Check for parent label
            parent_label = input_elem.find_parent('label')
            if parent_label:
                has_label = True
            
            if not has_label and not aria_label and not aria_labelledby:
                self.issues.append({
                    'type': 'Unlabeled Input',
                    'severity': 'High',
                    'element': str(input_elem)[:80] + '...',
                    'description': f'{input_elem.name} element lacks proper labeling',
                    'impact': 'Users cannot understand the purpose of this input',
                    'solution': 'Add a label element, aria-label, or aria-labelledby attribute',
                    'location': f'Form input {i+1}'
                })
    
    def check_clickable_elements(self):
        """Check for non-semantic clickable elements"""
        clickable_divs = self.soup.find_all('div', {'onclick': True})
        clickable_spans = self.soup.find_all('span', {'onclick': True})
        
        for i, elem in enumerate(clickable_divs + clickable_spans):
            role = elem.get('role')
            tabindex = elem.get('tabindex')
            
            issues_found = []
            if not role or role not in ['button', 'link']:
                issues_found.append('missing appropriate role')
            if tabindex is None or tabindex == '-1':
                issues_found.append('not keyboard accessible')
            
            if issues_found:
                self.issues.append({
                    'type': 'Non-semantic Clickable',
                    'severity': 'High',
                    'element': f'<{elem.name}>{elem.get_text()[:30]}...</{elem.name}>',
                    'description': f'Clickable {elem.name} element with issues: {", ".join(issues_found)}',
                    'impact': 'Element not accessible via keyboard or screen readers',
                    'solution': 'Use button/a elements or add role="button" and tabindex="0"',
                    'location': f'Clickable element {i+1}'
                })
    
    def check_color_contrast(self):
        """Basic color contrast check"""
        elements_with_style = self.soup.find_all(style=True)
        
        for i, elem in enumerate(elements_with_style):
            style = elem.get('style', '')
            if 'color:' in style and 'background' in style:
                self.issues.append({
                    'type': 'Potential Contrast Issue',
                    'severity': 'Medium',
                    'element': f'<{elem.name} style="{style[:40]}...">',
                    'description': 'Element has custom colors that may have contrast issues',
                    'impact': 'Text may be difficult to read for visually impaired users',
                    'solution': 'Verify color contrast ratio meets WCAG standards (4.5:1 for normal text)',
                    'location': f'Styled element {i+1}'
                })
    
    def check_links(self):
        """Check link accessibility"""
        links = self.soup.find_all('a')
        
        for i, link in enumerate(links):
            href = link.get('href')
            text = link.get_text().strip()
            
            if not href:
                self.issues.append({
                    'type': 'Link Without Href',
                    'severity': 'Medium',
                    'element': f'<a>{text[:30]}...</a>',
                    'description': 'Link element missing href attribute',
                    'impact': 'Link is not functional for keyboard users',
                    'solution': 'Add href attribute or use button element instead',
                    'location': f'Link {i+1}'
                })
            
            if not text and not link.get('aria-label'):
                self.issues.append({
                    'type': 'Empty Link Text',
                    'severity': 'High',
                    'element': f'<a href="{href}"></a>',
                    'description': 'Link has no accessible text',
                    'impact': 'Screen readers cannot describe the link purpose',
                    'solution': 'Add descriptive text or aria-label attribute',
                    'location': f'Link {i+1}'
                })
    
    def check_tables(self):
        """Check table accessibility"""
        tables = self.soup.find_all('table')
        
        for i, table in enumerate(tables):
            # Check for table headers
            headers = table.find_all('th')
            if not headers:
                self.issues.append({
                    'type': 'Table Without Headers',
                    'severity': 'Medium',
                    'element': '<table>...</table>',
                    'description': 'Table missing header cells (th elements)',
                    'impact': 'Screen readers cannot properly navigate table data',
                    'solution': 'Add th elements for column/row headers',
                    'location': f'Table {i+1}'
                })
            
            # Check for table caption
            caption = table.find('caption')
            if not caption:
                self.issues.append({
                    'type': 'Table Without Caption',
                    'severity': 'Low',
                    'element': '<table>...</table>',
                    'description': 'Table missing caption element',
                    'impact': 'Users may not understand table purpose',
                    'solution': 'Add caption element describing table content',
                    'location': f'Table {i+1}'
                })

def fetch_webpage(url):
    """Fetch webpage content"""
    try:
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return url, response.text, None
        
    except requests.exceptions.RequestException as e:
        return url, None, str(e)

def main():
    # Header
    st.title("🔍 Accessibility Analyzer")
    st.markdown("**Scan websites for accessibility issues and ensure your content is usable by everyone**")
    
    # Sidebar with information
    with st.sidebar:
        st.header("🛠️ What We Check")
        st.markdown("""
        **🖼️ Images**
        - Missing alt text
        - Empty alt attributes
        
        **🔡 Headings**
        - Proper hierarchy
        - Missing H1 tags
        - Level skipping
        
        **🧩 Forms**
        - Unlabeled inputs
        - Missing form labels
        
        **🖱️ Interactive Elements**
        - Non-semantic clickables
        - Keyboard accessibility
        
        **🔗 Links**
        - Empty link text
        - Missing href attributes
        
        **📊 Tables**
        - Missing headers
        - No captions
        
        **🎨 Colors**
        - Potential contrast issues
        """)
        
        st.header("📋 Severity Levels")
        st.error("**High:** Critical accessibility barriers")
        st.warning("**Medium:** Important usability issues")
        st.info("**Low:** Minor improvements needed")
    
    # Main content
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("🌐 Enter Website URL")
        url = st.text_input(
            "Website URL to analyze:",
            placeholder="https://example.com",
            help="Enter the full URL of the website you want to analyze"
        )
    
    with col2:
        st.header("🚀 Analysis")
        analyze_button = st.button("Analyze Website", type="primary", use_container_width=True)
    
    if analyze_button and url:
        with st.spinner("🔍 Fetching and analyzing website..."):
            # Fetch webpage
            final_url, html_content, error = fetch_webpage(url)
            
            if error:
                st.error(f"❌ **Error fetching website:** {error}")
                return
            
            if not html_content:
                st.error("❌ **No content received from website**")
                return
            
            # Analyze accessibility
            analyzer = AccessibilityAnalyzer(final_url, html_content)
            issues = analyzer.analyze()
            
            # Categorize issues
            high_issues = [issue for issue in issues if issue['severity'] == 'High']
            medium_issues = [issue for issue in issues if issue['severity'] == 'Medium']
            low_issues = [issue for issue in issues if issue['severity'] == 'Low']
            
            # Display results
            st.success(f"✅ **Analysis completed for:** {final_url}")
            
            # Summary metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Issues", len(issues))
            with col2:
                st.metric("High Priority", len(high_issues), delta=f"-{len(high_issues)}" if high_issues else "0")
            with col3:
                st.metric("Medium Priority", len(medium_issues), delta=f"-{len(medium_issues)}" if medium_issues else "0")
            with col4:
                st.metric("Low Priority", len(low_issues), delta=f"-{len(low_issues)}" if low_issues else "0")
            
            if not issues:
                st.balloons()
                st.success("🎉 **Congratulations!** No accessibility issues found!")
                st.info("This website appears to follow good accessibility practices.")
                return
            
            # Tabs for different severity levels
            tab1, tab2, tab3, tab4 = st.tabs([
                f"🔴 High Priority ({len(high_issues)})",
                f"🟡 Medium Priority ({len(medium_issues)})",
                f"🔵 Low Priority ({len(low_issues)})",
                f"📊 All Issues ({len(issues)})"
            ])
            
            def display_issues(issues_list, severity_color="red"):
                if not issues_list:
                    st.info(f"🎉 No {severity_color} priority issues found!")
                    return
                
                for i, issue in enumerate(issues_list):
                    with st.expander(f"**{issue['type']}** - {issue['location']}", expanded=i < 3):
                        col1, col2 = st.columns([3, 1])
                        
                        with col1:
                            st.markdown(f"**Description:** {issue['description']}")
                            st.code(issue['element'], language='html')
                            st.markdown(f"**Impact:** {issue['impact']}")
                            st.markdown(f"**Solution:** {issue['solution']}")
                        
                        with col2:
                            severity_color_map = {
                                'High': 'red',
                                'Medium': 'orange', 
                                'Low': 'blue'
                            }
                            st.markdown(f"**Severity**")
                            st.markdown(f":{severity_color_map[issue['severity']]}[{issue['severity']}]")
                            st.markdown(f"**Location**")
                            st.markdown(issue['location'])
            
            with tab1:
                st.markdown("### 🔴 High Priority Issues")
                st.markdown("These issues create significant barriers for users with disabilities and should be fixed immediately.")
                display_issues(high_issues, "high")
            
            with tab2:
                st.markdown("### 🟡 Medium Priority Issues")
                st.markdown("These issues impact usability and should be addressed soon.")
                display_issues(medium_issues, "medium")
            
            with tab3:
                st.markdown("### 🔵 Low Priority Issues")
                st.markdown("These are minor improvements that enhance accessibility.")
                display_issues(low_issues, "low")
            
            with tab4:
                st.markdown("### 📊 All Issues Summary")
                
                # Create DataFrame for download
                df_data = []
                for issue in issues:
                    df_data.append({
                        'Type': issue['type'],
                        'Severity': issue['severity'],
                        'Location': issue['location'],
                        'Description': issue['description'],
                        'Impact': issue['impact'],
                        'Solution': issue['solution']
                    })
                
                if df_data:
                    df = pd.DataFrame(df_data)
                    st.dataframe(df, use_container_width=True)
                    
                    # Download button
                    csv = df.to_csv(index=False)
                    st.download_button(
                        label="📥 Download Report as CSV",
                        data=csv,
                        file_name=f"accessibility_report_{urlparse(final_url).netloc}_{int(time.time())}.csv",
                        mime="text/csv"
                    )
    
    elif analyze_button and not url:
        st.warning("⚠️ Please enter a website URL to analyze.")
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666;'>
        <p>🔍 Accessibility Analyzer | Making the web accessible for everyone</p>
        <p>Built with ❤️ using Streamlit</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
