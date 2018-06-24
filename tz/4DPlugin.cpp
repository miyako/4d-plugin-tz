/* --------------------------------------------------------------------------------
 #
 #	4DPlugin.cpp
 #	source generated by 4D Plugin Wizard
 #	Project : TZ
 #	author : miyako
 #	2018/06/24
 #
 # --------------------------------------------------------------------------------*/


#include "4DPluginAPI.h"
#include "4DPlugin.h"

void PluginMain(PA_long32 selector, PA_PluginParameters params)
{
	try
	{
		PA_long32 pProcNum = selector;
		sLONG_PTR *pResult = (sLONG_PTR *)params->fResult;
		PackagePtr pParams = (PackagePtr)params->fParameters;

		CommandDispatcher(pProcNum, pResult, pParams); 
	}
	catch(...)
	{

	}
}

void CommandDispatcher (PA_long32 pProcNum, sLONG_PTR *pResult, PackagePtr pParams)
{
	switch(pProcNum)
	{
		case kInitPlugin :
		case kServerInitPlugin :
			OnStartup();
			break;
			
// --- TZ

		case 1 :
			TZ_Convert(pResult, pParams);
			break;

		case 2:
			TZ_Get_zones(pResult, pParams);
			break;
	}
}

// -------------------------------------- TZ --------------------------------------

void OnStartup()
{
#if VERSIONMAC
#define THIS_BUNDLE_ID @"com.4D.tz"
	NSBundle *thisBundle = [NSBundle bundleWithIdentifier : THIS_BUNDLE_ID];
	if (thisBundle)
	{
		NSString *resourcePath = [thisBundle resourcePath];
		if (resourcePath)
		{
			NSString *installPath = [resourcePath stringByAppendingPathComponent : @"tzdata"];
			std::string path = [installPath UTF8String];

			using namespace date;
			set_install(path);
		}
	}
#else
#define THIS_BUNDLE_NAME L"TZ.4DX"
#define LIBTZ_OPEN_UTF8 0
#if LIBTZ_OPEN_UTF8
#define OPEN_CP CP_UTF8
#else
#define OPEN_CP CP_ACP
#endif
	wchar_t	fDrive[_MAX_DRIVE], fDir[_MAX_DIR], fName[_MAX_FNAME], fExt[_MAX_EXT];
	wchar_t thisPath[_MAX_PATH] = { 0 };
	HMODULE hplugin = GetModuleHandleW(THIS_BUNDLE_NAME);

	if (hplugin)
	{
		using namespace std;
		GetModuleFileNameW(hplugin, thisPath, _MAX_PATH);
		_wsplitpath_s(thisPath, fDrive, fDir, fName, fExt);
		wstring windowsPath = fDrive;
		windowsPath += fDir;
		//remove delimiter to go one level up the hierarchy
		if (windowsPath.at(windowsPath.size() - 1) == L'\\')
			windowsPath = windowsPath.substr(0, windowsPath.size() - 1);

		_wsplitpath_s(windowsPath.c_str(), fDrive, fDir, fName, fExt);
		wstring resourcesPath = fDrive;
		resourcesPath += fDir;
		resourcesPath += L"Resources\\tzdata\\";

		//is it really utf-8?
		int len = WideCharToMultiByte(OPEN_CP, 0, (LPCWSTR)resourcesPath.c_str(), resourcesPath.length(), NULL, 0, NULL, NULL);

		if (len) {
			std::vector<uint8_t> buf(len + 1);
			if (WideCharToMultiByte(OPEN_CP, 0, (LPCWSTR)resourcesPath.c_str(), resourcesPath.length(), (LPSTR)&buf[0], len, NULL, NULL))
			{
				string path = string((const char *)&buf[0]);
				using namespace date;
				set_install(path);
			}
		}

	}
#endif
}

void get_zone_names(C_TEXT &names)
{
	using namespace date;
	using namespace std;
	using namespace std::chrono;
	
	auto now = floor<milliseconds>(system_clock::now());
	
	JSONNODE *n = json_new(JSON_ARRAY);
	
	for(auto i = get_tzdb().zones.begin(); i != get_tzdb().zones.end();++i)
	{
		JSONNODE *tz = json_new(JSON_NODE);
		//name
		json_set_s_for_key(tz, L"name", i->name().c_str());
		
		//abbrev
		sys_info si = i->get_info(now);
		string abbrev = si.abbrev;
		json_set_s_for_key(tz, L"abbrev", abbrev.c_str());
		
		//to_local
		ostringstream local;
		local << i->to_local(now);
		json_set_s_for_key(tz, L"local_time", local.str().c_str());
		
		//offset
		ostringstream offset_t;
		offset_t << format("%T", si.offset);
		json_set_s_for_key(tz, L"offset_time", offset_t.str().c_str());
		
		ostringstream offset_s;
		offset_s << si.offset;
		json_set_i_for_key(tz, L"offset", atoi(offset_s.str().c_str()));
		
		//save
		ostringstream save_t;
		save_t << format("%T", si.save);
		json_set_s_for_key(tz, L"save_time", save_t.str().c_str());
		
		ostringstream save_s;
		save_s << si.save;
		json_set_i_for_key(tz, L"save", atoi(save_s.str().c_str()));
		
		//begin
		ostringstream begin;
		begin << si.begin;
		json_set_s_for_key(tz, L"begin", begin.str().c_str());
		
		//end
		ostringstream end;
		end << si.end;
		json_set_s_for_key(tz, L"end", end.str().c_str());
		
		json_push_back(n, tz);
	}

	json_stringify(n, names);
	json_delete(n);
}

/* deactivated (curl dependency) */

void parse_date(C_TEXT &date_in,
								C_TEXT &format_in,
								C_TEXT &date_out,
								C_TEXT &zone_out,
								C_TEXT &format_out,
								C_LONGINT &time_to_add)
{
	CUTF8String u8;
	date_in.copyUTF8String(&u8);
	
	using namespace date;
	using namespace std;
	using namespace std::chrono;
	
	sys_time<milliseconds> t;
	
	//parse date_in using format_in
	istringstream stream{std::string((const char *)u8.c_str(), u8.length())};
	format_in.copyUTF8String(&u8);
	stream >> parse((const char *)u8.c_str(), t);

	if(!stream.fail())
	{
		//parse successful
		t += seconds{time_to_add.getIntValue()};
		
		std::string result;
		
		if(zone_out.getUTF16Length())
		{
			//zone_out specified
			zone_out.copyUTF8String(&u8);
			try{
				//make_zoned can throw exception with extream cases
				auto tz = make_zoned((const char *)u8.c_str(), t);
				if(format_out.getUTF16Length())
				{
					//format_out specified
					format_out.copyUTF8String(&u8);
					result = format((const char *)u8.c_str(), tz);
				}else
				{
					//format_out not specified
					ostringstream s;
					s << tz;
					result = s.str();
				}
			}catch(...){}
		}
		
		if(!result.length())
		{
			//zone_out was not specified or threw an exception
			if(format_out.getUTF16Length())
			{
				//format_out specified
				format_out.copyUTF8String(&u8);
				result = format((const char *)u8.c_str(), t);
			}else
			{
				//format_out not specified
				ostringstream s;
				s << t;
				result = s.str();
			}
			
		}
		
		date_out.setUTF8String((const uint8_t *)result.c_str(), result.length());
	}
}

void TZ_Convert(sLONG_PTR *pResult, PackagePtr pParams)
{
	C_TEXT Param1;
	C_TEXT Param2;
	C_TEXT Param3;
	C_TEXT Param4;
	C_LONGINT Param5;
	C_TEXT returnValue;
	
	Param1.fromParamAtIndex(pParams, 1);
	Param2.fromParamAtIndex(pParams, 2);
	Param3.fromParamAtIndex(pParams, 3);
	Param4.fromParamAtIndex(pParams, 4);
	Param5.fromParamAtIndex(pParams, 5);
	
	parse_date(Param1/* date_in */,
						 Param2/* format_in */,
						 returnValue/* date_out */,
						 Param3/* zone_out */,
						 Param4/* format_out */,
						 Param5/* time_to_add */);
	
	returnValue.setReturn(pResult);
}

void TZ_Get_zones(sLONG_PTR *pResult, PackagePtr pParams)
{
	C_TEXT returnValue;
	
	get_zone_names(returnValue);
	
	returnValue.setReturn(pResult);
}
