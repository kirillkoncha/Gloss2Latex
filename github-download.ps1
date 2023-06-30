$tex_repos = @()
$page = 1
$repos = "start"
while($repos)
{
    $repos = gh api -XGET -H "Accept: application/vnd.github+json" -H "X-GitHub-Api-Version: 2022-11-28" /orgs/langsci/repos -F per_page=100 -F page=$page | ConvertFrom-Json
	$repos | ForEach-Object {
		"Lang is $($_.language), clone URL: $($_.clone_url)"
		if ($_.language -eq "TeX"){ 
			$tex_repos += $_.clone_url
		} 
	}
	
	$page++
}
