import requests 
from bs4 import BeautifulSoup
import time 
import re 
from PIL import Image, ImageDraw, ImageFont

class FCSBethuneScraper:
    def __init__(self):
        self.session = requests.session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
        })

        self.fcs_stats_urls = {
            'Scoring Offense': 'https://www.ncaa.com/stats/football/Fcs/current/team/27',
            'Total Offense': 'https://www.ncaa.com/stats/football/Fcs/current/team/21',
            'Rushing Offense': 'https://www.ncaa.com/stats/football/Fcs/current/team/23',
            'Passing Offense': 'https://www.ncaa.com/stats/football/Fcs/current/team/25',
            'Time of Possession': 'https://www.ncaa.com/stats/football/Fcs/current/team/705',
            'Third Down Conversions': 'https://www.ncaa.com/stats/football/Fcs/current/team/699',
            'Red Zone Offense': 'https://www.ncaa.com/stats/football/Fcs/current/team/703',
            'Sacks Allowed': 'https://www.ncaa.com/stats/football/Fcs/current/team/468',
            'Scoring Defense': 'https://www.ncaa.com/stats/football/Fcs/current/team/28',
            'Total Defense': 'https://www.ncaa.com/stats/football/Fcs/current/team/22',
            'Rushing Defense': 'https://www.ncaa.com/stats/football/Fcs/current/team/24',
            'Passing Yards Allowed': 'https://www.ncaa.com/stats/football/Fcs/current/team/695',
            'Third Down Conversions Defense': 'https://www.ncaa.com/stats/football/Fcs/current/team/701',
            'Red Zone Defense': 'https://www.ncaa.com/stats/football/Fcs/current/team/704',
            'Sacks Per Game': 'https://www.ncaa.com/stats/football/Fcs/current/team/466',
            'Turnover Margin': 'https://www.ncaa.com/stats/football/Fcs/current/team/29',
            'Fewest Penalties Per Game': 'https://www.ncaa.com/stats/football/Fcs/current/team/697',
            'Fewest Penalty Yards Per Game': 'https://www.ncaa.com/stats/football/Fcs/current/team/698'
        }

    def scrape_stat_ranking(self, stat_name, team_name):
        if stat_name not in self.fcs_stats_urls:
            print(f"No URL exists: {stat_name}")
            return None, None
        
        url = self.fcs_stats_urls[stat_name]
        print(f"Scraping {stat_name} from {url}")

        try:
            for page_suffix in ['', '/p2', '/p3', '/p4']:
                test_url = url + page_suffix
                response = self.session.get(test_url, timeout=15)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    stat_value, ranking = self.find_team_in_fcs_rankings(soup, team_name, stat_name)
                    if stat_value and ranking:
                        return stat_value, ranking
                time.sleep(1)

            print(f"Could not find: {team_name} in {stat_name}")
            return None, None
        except Exception as e:
            print(f"Error scraping {stat_name} for {team_name}: {e}")
            return None, None
        
    def find_team_in_fcs_rankings(self, soup, team_name, stat_name):
        clean_team_names = self.clean_team_name(team_name)
        tables = soup.find_all('table')
        
        for table in tables:
            rows = table.find_all('tr')
            
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 3:  
                    
                    row_text = ' '.join(cell.get_text().strip() for cell in cells)
                    
                    if self.team_matches(row_text, clean_team_names, team_name):
                        try:
                            print(f"Found row for {team_name}: {[cell.get_text().strip() for cell in cells]}")
                            
                            rank = cells[0].get_text().strip()
                            
                            if rank == "-":
                                rank = self.find_tied_rank(table, row, team_name)
                                if not rank:
                                    print(f"Could not determine tied rank for {team_name}")
                                    continue
                            else:
                                rank_clean = re.sub(r'[^\d]', '', rank)
                                if not rank_clean.isdigit():
                                    print(f"Could not parse rank: {rank}")
                                    continue
                                rank = rank_clean
                            
                            stat_value = None
                            
                            for i in range(len(cells) - 1, 0, -1):
                                cell_text = cells[i].get_text().strip()
                                
                                if re.match(r'^\d+\.?\d*$', cell_text):
                                    stat_value = cell_text
                                    break
                                
                                if ':' in cell_text and stat_name == 'Time of Possession':
                                    stat_value = cell_text
                                    break
                                
                                if cell_text.startswith('.') and len(cell_text) > 1 and re.match(r'^\.\d+$', cell_text):
                                    stat_value = cell_text
                                    break
                                
                                if re.match(r'^[+-]\d+\.?\d*$', cell_text):
                                    stat_value = cell_text
                                    break
                            
                            if rank and stat_value:
                                ranking_str = f"({rank}/119)"
                                
                                print(f"Found {team_name}: {stat_value} {ranking_str}")
                                return stat_value, ranking_str
                            else:
                                print(f"Could not extract rank ({rank}) or stat value ({stat_value}) for {team_name}")
                        
                        except Exception as e:
                            print(f"Error parsing row for {team_name}: {e}")
                            continue
        
        return None, None
    
    def find_tied_rank(self, table, current_row, team_name):
        """Find the actual rank for tied teams (when rank shows as '-')"""
        rows = table.find_all('tr')
        current_row_index = -1
        
        for i, row in enumerate(rows):
            if row == current_row:
                current_row_index = i
                break
        
        if current_row_index == -1:
            return None
        
        for i in range(current_row_index - 1, -1, -1):
            cells = rows[i].find_all(['td', 'th'])
            if len(cells) >= 1:
                rank_text = cells[0].get_text().strip()
                if rank_text.isdigit():
                    tied_teams = self.count_tied_teams(table, current_row_index)
                    actual_rank = int(rank_text) + 1 
                    print(f"Found tied rank for {team_name}: {actual_rank} (tied with {tied_teams} teams)")
                    return str(actual_rank)
        
        return "1"
    
    def count_tied_teams(self, table, current_row_index):
        """Count how many teams are tied at the current position"""
        rows = table.find_all('tr')
        tied_count = 0
        
        for i in range(current_row_index, len(rows)):
            cells = rows[i].find_all(['td', 'th'])
            if len(cells) >= 1:
                rank_text = cells[0].get_text().strip()
                if rank_text == "-":
                    tied_count += 1
                else:
                    break
        
        return tied_count
    
    def clean_team_name(self, team_name):
        """Clean team name for better matching"""
        replacements = {
            'Bethune-Cookman': ['Bethune Cookman', 'Bethune-Cookman', 'BCU'],
            'Alabama A&M': ['Alabama A&M', 'Alabama AM', 'AAMU', 'Ala. A&M']
        }

        if team_name in replacements:
            return replacements[team_name]
        
        return [team_name, team_name.replace('-', ' '), team_name.replace('&', 'and')]
    
    def team_matches(self, row_text, clean_names, original_name):
        row_lower = row_text.lower()

        for name_variation in clean_names:
            if name_variation.lower() in row_lower:
                return True
            
        name_parts = original_name.lower().split()
        if len(name_parts) > 1:
            return all(part in row_lower for part in name_parts)
        return False
    
    def count_teams_in_table(self, table):
        rows = table.find_all('tr')
        team_count = 0

        for row in rows:
            cells = row.find_all(['td', 'th'])
            if len(cells) >= 3:
                first_cell = cells[0].get_text().strip()
                if first_cell.isdigit():
                    team_count = max(team_count, int(first_cell))
        return team_count if team_count > 0 else 125
    
    def scrape_all_fcs_team_stats(self, team_name):
        print(f"\nScraping all FCS stats for {team_name}")
        print("=" * 60)
        team_stats = {}

        for stat_name in self.fcs_stats_urls.keys():
            stat_value, ranking = self.scrape_stat_ranking(stat_name, team_name)

            if stat_value and ranking:
                team_stats[stat_name] = (stat_value, ranking)
            else:
                team_stats[stat_name] = 'N/A'
            
            time.sleep(1)
        return team_stats
    
    def print_team_stats(self, team_name):
        stats = self.scrape_all_fcs_team_stats(team_name)

        print (f"\n{team_name.upper()} - FCS NATIONAL RANKINGS")
        print("=" *70)

        for stat_name, stat_data in stats.items():
            if isinstance(stat_data, tuple):
                value, ranking = stat_data
                print(f"{stat_name:<35} {value} {ranking}")
            else:
                print(f"{stat_name:<35} {stat_data}")

        return stats
    
    def compare_teams(self, team1_name, team2_name):
        print(f"Comparing {team1_name} vs {team2_name} - FCS NATIONAL RANKINGS")
        print("=" *80)

        team1_stats = self.scrape_all_fcs_team_stats(team1_name)
        print("\n" + "="*60 + "\n")
        team2_stats = self.scrape_all_fcs_team_stats(team2_name)

        print(f"\n{team1_name.upper()} vs {team2_name.upper()} - FCS COMPARISON")
        print("=" * 90)
        print(f"{'Statistic':<35} {team1_name:<25} {team2_name}")
        print("-" * 90)
        
        for stat_name in self.fcs_stats_urls.keys():
            team1_val = team1_stats.get(stat_name, 'N/A')
            team2_val = team2_stats.get(stat_name, 'N/A')
            
            team1_str = self.format_stat_display(team1_val)
            team2_str = self.format_stat_display(team2_val)
            
            print(f"{stat_name:<35} {team1_str:<25} {team2_str}")
        
        return team1_stats, team2_stats
    
    def format_stat_display(self, stat_data):
        if isinstance(stat_data, tuple):
            value, ranking = stat_data
            return f"{value} {ranking}"
        else:
            return str(stat_data)
        
    def create_comparison_image(self, team1_name, team2_name, team1_stats, team2_stats, filename=None):
        if filename is None:
            filename = f"{team1_name.replace(' ', '_')}_vs_{team2_name.replace(' ', '_')}_FCS_comparison.jpg"
        
        img_width = 950
        img_height = 700

        red_header = (128, 0, 32)
        white = (255, 215, 0)
        black = (0, 0, 0)
        light_gray = (240, 240, 240)
        
        img = Image.new('RGB', (img_width, img_height), white)
        draw = ImageDraw.Draw(img)
        
        try:
            header_font = ImageFont.truetype("arial.ttf", 22)
            team_font = ImageFont.truetype("arial.ttf", 18)
            stat_font = ImageFont.truetype("arial.ttf", 13)
        except:
            header_font = ImageFont.load_default()
            team_font = ImageFont.load_default()
            stat_font = ImageFont.load_default()
        
        
        header_height = 60
        draw.rectangle([(0, 0), (img_width, header_height)], fill=red_header)
        
        header_text = f"{team1_name.upper()}-{team2_name.upper()} FCS STATISTICS AND NOTES"
        draw.text((70, 18), header_text, fill=white, font=header_font)
        
        section_y = header_height + 20
        draw.text((20, section_y), "▶ STAT COMPARISON (FCS NATIONAL RANK)", fill=black, font=team_font)
        
        col_y = section_y + 40
        draw.text((50, col_y), team1_name, fill=black, font=team_font)
        draw.text((img_width - 250, col_y), team2_name, fill=black, font=team_font)
        
        line_y = col_y + 30
        draw.line([(20, line_y), (img_width - 20, line_y)], fill=black, width=1)
        
        current_y = line_y + 15
        row_height = 28
        
        for i, stat_name in enumerate(self.fcs_stats_urls.keys()):
            if current_y > img_height - 50:
                break
                
            if i % 2 == 0:
                draw.rectangle([(0, current_y - 5), (img_width, current_y + row_height - 5)], 
                             fill=light_gray)
            
            draw.text((30, current_y), stat_name, fill=black, font=stat_font)
            
            team1_data = team1_stats.get(stat_name, 'N/A')
            team1_text = self.format_stat_display(team1_data)
            draw.text((400, current_y), team1_text, fill=black, font=stat_font)
            
            team2_data = team2_stats.get(stat_name, 'N/A')
            team2_text = self.format_stat_display(team2_data)
            draw.text((650, current_y), team2_text, fill=black, font=stat_font)
            
            current_y += row_height
        
        img.save(filename, 'JPEG', quality=95)
        print(f"\nFCS comparison chart saved as: {filename}")
        
        return filename
    
def scrape_fcs_team_stats(team_name):
    scraper = FCSBethuneScraper()
    return scraper.print_team_stats(team_name)

def compare_fcs_teams(team1_name, team2_name, create_image=True):
    scraper = FCSBethuneScraper()
    team1_stats, team2_stats = scraper.compare_teams(team1_name, team2_name)

    if create_image:
        scraper.create_comparison_image(team1_name, team2_name, team1_stats, team2_stats)

    return team1_stats, team2_stats

if __name__ == "__main__":
    print("FCS Football Stats Scraper")
    print("=" *40)

    compare_fcs_teams("Bethune-Cookman", "Alabama A&M", create_image=True)
